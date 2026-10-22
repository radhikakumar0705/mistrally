/** The file name from a Content-Disposition header, e.g. `attachment; filename="notes.md"`. */
export function filenameFromDisposition(header: string | null | undefined, fallback: string): string {
  const match = /filename="?([^";]+)"?/i.exec(header ?? "");
  return match?.[1]?.trim() || fallback;
}

/** Save a Blob as a file via a temporary link. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
