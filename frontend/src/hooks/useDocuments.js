import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { errorMessage } from "../api/axiosClient";
import { deleteDocument, getDocuments, uploadDocument } from "../api/documents";

/** The user's uploaded documents, which Mistrally searches when answering (RAG). */
export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    getDocuments()
      .then(setDocuments)
      .catch(() => {}); // the panel just stays empty if the document store is down
  }, []);

  const upload = useCallback(async (file) => {
    setUploading(true);
    const toastId = toast.loading(`Reading ${file.name}…`);
    try {
      const document = await uploadDocument(file);
      setDocuments((prev) => [document, ...prev]);
      toast.success(`Added ${document.filename}`, {
        id: toastId,
        description: "Ask a question about it and Mistrally will use it.",
      });
    } catch (error) {
      toast.error(errorMessage(error, "Upload failed"), { id: toastId });
    } finally {
      setUploading(false);
    }
  }, []);

  const remove = useCallback(async (document) => {
    try {
      await deleteDocument(document.id);
      setDocuments((prev) => prev.filter((d) => d.id !== document.id));
      toast.success(`Removed ${document.filename}`);
    } catch (error) {
      toast.error(errorMessage(error, "Could not remove that document"));
    }
  }, []);

  return { documents, uploading, upload, remove };
}
