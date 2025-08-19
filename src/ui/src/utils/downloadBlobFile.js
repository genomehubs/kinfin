export const downloadBlobFile = (
  blob,
  filename,
  mimeType = "application/octet-stream"
) => {
  const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
  const a = document.createElement("a");

  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  window.URL.revokeObjectURL(url);
};
