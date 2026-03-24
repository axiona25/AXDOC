const MAX_DIMENSION = 2048
const MAX_SIZE_BYTES = 2 * 1024 * 1024 // 2MB
const JPEG_QUALITY = 0.80
const PNG_TO_JPEG_QUALITY = 0.85

/**
 * Comprimi un'immagine nel browser usando Canvas API.
 * Ritorna il File compresso oppure l'originale se non è un'immagine o la compressione fallisce.
 */
export async function compressImage(file: File): Promise<File> {
  // Solo immagini
  if (!file.type.startsWith('image/')) return file
  // Skip GIF (animazioni) e SVG (vettoriale)
  if (file.type === 'image/gif' || file.type === 'image/svg+xml') return file
  // Se già piccola, non comprimere
  if (file.size <= MAX_SIZE_BYTES) {
    // Controlla comunque le dimensioni
    const needsResize = await checkNeedsResize(file)
    if (!needsResize) return file
  }

  try {
    const bitmap = await createImageBitmap(file)
    const { width, height } = bitmap

    // Calcola nuove dimensioni mantenendo aspect ratio
    let newWidth = width
    let newHeight = height
    if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
      const ratio = Math.min(MAX_DIMENSION / width, MAX_DIMENSION / height)
      newWidth = Math.round(width * ratio)
      newHeight = Math.round(height * ratio)
    }

    // Canvas
    const canvas = document.createElement('canvas')
    canvas.width = newWidth
    canvas.height = newHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return file

    ctx.drawImage(bitmap, 0, 0, newWidth, newHeight)
    bitmap.close()

    // Determina formato output
    let outputType = file.type
    let quality = JPEG_QUALITY

    // PNG grandi → converti a JPEG
    if (file.type === 'image/png' && file.size > MAX_SIZE_BYTES) {
      outputType = 'image/jpeg'
      quality = PNG_TO_JPEG_QUALITY
    }

    // WebP mantieni WebP
    if (file.type === 'image/webp') {
      outputType = 'image/webp'
      quality = JPEG_QUALITY
    }

    // Converti a blob
    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, outputType, quality)
    })

    if (!blob || blob.size >= file.size) {
      // Compressione non ha ridotto — usa originale
      return file
    }

    // Aggiorna estensione se convertito
    let fileName = file.name
    if (file.type === 'image/png' && outputType === 'image/jpeg') {
      fileName = fileName.replace(/\.png$/i, '.jpg')
    }

    const compressed = new File([blob], fileName, {
      type: outputType,
      lastModified: Date.now(),
    })

    console.log(
      `[ImageCompressor] ${file.name}: ${(file.size / 1024).toFixed(0)}KB → ${(compressed.size / 1024).toFixed(0)}KB (${Math.round((1 - compressed.size / file.size) * 100)}% riduzione)`
    )

    return compressed
  } catch (err) {
    console.warn('[ImageCompressor] Compressione fallita, uso originale:', err)
    return file
  }
}

async function checkNeedsResize(file: File): Promise<boolean> {
  try {
    const bitmap = await createImageBitmap(file)
    const needsResize = bitmap.width > MAX_DIMENSION || bitmap.height > MAX_DIMENSION
    bitmap.close()
    return needsResize
  } catch {
    return false
  }
}

/**
 * Comprimi un array di file. I non-immagini passano inalterati.
 */
export async function compressFiles(files: File[]): Promise<File[]> {
  return Promise.all(files.map(compressImage))
}
