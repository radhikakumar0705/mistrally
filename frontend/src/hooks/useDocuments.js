import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { errorMessage } from "../api/axiosClient";
import { deleteDocument, getDocuments, uploadDocument } from "../api/documents";

const POLL_MS = 1500;
const isPending = (doc) => doc.status === "queued" || doc.status === "processing";

/**
 * The user's uploaded documents, which Mistrally searches when answering (RAG).
 * Uploads are processed in the background, so pending documents are polled until they finish.
 */
export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const previous = useRef(new Map());

  const refresh = useCallback(async () => {
    try {
      const latest = await getDocuments();
      // Announce documents that just finished processing
      for (const doc of latest) {
        const before = previous.current.get(doc.id);
        if (before && isPending(before) && doc.status === "ready") {
          toast.success(`${doc.filename} is ready`, { description: "Ask a question about it." });
        } else if (before && isPending(before) && doc.status === "failed") {
          toast.error(`Couldn't process ${doc.filename}`, { description: doc.error });
        }
      }
      previous.current = new Map(latest.map((d) => [d.id, d]));
      setDocuments(latest);
    } catch {
      // the panel keeps its last known state if the API is briefly unavailable
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const hasPending = documents.some(isPending);
  useEffect(() => {
    if (!hasPending) return undefined;
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [hasPending, refresh]);

  const upload = useCallback(
    async (file) => {
      setUploading(true);
      try {
        const document = await uploadDocument(file);
        previous.current.set(document.id, document);
        setDocuments((prev) => [document, ...prev.filter((d) => d.id !== document.id)]);
        if (document.status === "ready") {
          toast.success(`Added ${document.filename}`, { description: "Ask a question about it." });
        } else {
          toast(`Processing ${document.filename}…`, { description: "You can keep chatting meanwhile." });
        }
      } catch (error) {
        toast.error(errorMessage(error, "Upload failed"));
        refresh();
      } finally {
        setUploading(false);
      }
    },
    [refresh]
  );

  const remove = useCallback(async (document) => {
    try {
      await deleteDocument(document.id);
      previous.current.delete(document.id);
      setDocuments((prev) => prev.filter((d) => d.id !== document.id));
      toast.success(`Removed ${document.filename}`);
    } catch (error) {
      toast.error(errorMessage(error, "Could not remove that document"));
    }
  }, []);

  return { documents, readyCount: documents.filter((d) => d.status === "ready").length, uploading, upload, remove };
}
