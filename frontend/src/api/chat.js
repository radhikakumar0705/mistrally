import axiosClient from "./axiosClient";

const chat = {
  sendMessage: async (message) => {
    const token = localStorage.getItem("token");
    const response = await axiosClient.post(
      "/chat/send",
      { message },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },

  getHistory: async () => {
    const token = localStorage.getItem("token");
    const response = await axiosClient.get("/chat/history", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },
};

export default chat;
