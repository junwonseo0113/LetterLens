// Re-encode a photo in the browser before upload: at most 2000px on the
// long side as JPEG. Keeps typical uploads under 1 MB, which the server
// holds in memory instead of spilling to a temporary file on disk, and
// re-drawing drops the photo's metadata (e.g. GPS location). Falls back to
// the original file if the browser can't do it.
export async function shrinkImage(file, maxSide = 2000, quality = 0.85) {
  if (!file?.type?.startsWith("image/") || typeof createImageBitmap !== "function") return file;
  let bitmap;
  const canvas = document.createElement("canvas");
  try {
    bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
    return blob || file;
  } catch {
    return file;
  } finally {
    bitmap?.close();
    // Release the canvas pixels.
    canvas.width = 0;
    canvas.height = 0;
  }
}
