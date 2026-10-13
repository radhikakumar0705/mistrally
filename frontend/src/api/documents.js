import axiosClient from "./axiosClient";

export const getDocuments = async () => (await axiosClient.get("/documents")).data;

export const uploadDocument = async (file) => {
  const form = new FormData();
  form.append("file", file);
  return (await axiosClient.post("/documents", form)).data;
};

export const deleteDocument = (documentId) => axiosClient.delete(`/documents/${documentId}`);
