import axios from "axios";

// Environment-aware API configuration
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD
    ? "https://talk2pdf-backend.onrender.com" // Replace with your Render URL
    : "http://localhost:8000");

// Add timeout and better error handling
const axiosConfig = {
  timeout: 60000, // Increased to 60 seconds for complex queries
  headers: {
    "Content-Type": "application/json",
  },
};

export const uploadPDF = async (file) => {
  try {
    console.log(
      "Starting upload for file:",
      file.name,
      "Size:",
      file.size,
      "Type:",
      file.type
    );

    const formData = new FormData();
    formData.append("file", file); // must match FastAPI parameter name

    console.log("Sending upload request to:", `${API_BASE_URL}/upload`);

    const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 30000, // Reduced timeout since upload should be fast now
    });

    console.log("Upload response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Upload error details:", {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
      code: error.code,
      config: error.config,
      url: `${API_BASE_URL}/upload`,
      fileInfo: {
        name: file?.name,
        size: file?.size,
        type: file?.type,
      },
    });
    throw error;
  }
};

// New function to check processing status
export const checkProcessingStatus = async (docId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/status/${docId}`, {
      timeout: 5000,
    });
    return response.data;
  } catch (error) {
    console.error("Status check error:", error);
    throw error;
  }
};

export const askQuestion = async (doc_id, question) => {
  try {
    console.log("Asking question:", { doc_id, question });

    const response = await axios.post(
      `${API_BASE_URL}/ask`,
      {
        doc_id,
        question,
      },
      axiosConfig
    );

    console.log("Question response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Ask question error details:", {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
      url: `${API_BASE_URL}/ask`,
      requestData: { doc_id, question },
    });
    throw error;
  }
};

// Test function to check backend connection
export const testConnection = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`, {
      timeout: 10000, // Increased to 10 seconds
      withCredentials: false, // Explicitly disable credentials
    });
    console.log("Backend health check:", response.data);

    // Check if the response indicates a healthy backend
    const isHealthy =
      response.status === 200 && response.data && response.data.status === "ok";

    return {
      connected: isHealthy,
      status: response.data,
      error: null,
    };
  } catch (error) {
    console.error("Backend connection test failed:", error);
    return {
      connected: false,
      status: null,
      error: error.message || "Unknown error",
    };
  }
};

// Server cleanup function for storage issues
export const cleanupServer = async () => {
  try {
    console.log("Requesting server cleanup...");
    const response = await axios.post(`${API_BASE_URL}/cleanup-server`, {}, {
      timeout: 30000, // 30 seconds for cleanup
    });
    console.log("Cleanup response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Server cleanup error:", error);
    throw error;
  }
};
