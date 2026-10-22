import axiosClient from "./axiosClient";
import type { DocumentRecord } from "./types";

export const getDocuments = async () => (await axiosClient.get<DocumentRecord[]>("/documents")).data;

export const uploadDocument = async (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return (await axiosClient.post<DocumentRecord>("/documents", form)).data;
};

export const deleteDocument = (documentId: string) => axiosClient.delete(`/documents/${documentId}`);
