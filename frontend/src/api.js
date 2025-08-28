import axios from "axios";

const API_BASE_URL = "http://localhost:5000"; // backend URL

export const uploadPDF = async (file) => {
  const formData = new FormData();
  formData.append("file", file); // must match FastAPI parameter name

  const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data;
};

export const askQuestion = async (question) => {
  const response = await axios.post(`${API_BASE_URL}/ask`, { question });
  return response.data;
};
