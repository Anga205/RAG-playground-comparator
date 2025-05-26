"use client";

import { useState } from "react";
import SparkMD5 from 'spark-md5';

const BACKEND_URL = "http://localhost:8000";
const UPLOAD_CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks
const MAX_TOTAL_FILE_SIZE = 100 * 1024 * 1024; // 100MB total file size limit

// Helper function to calculate MD5 using SparkMD5
const calculateMD5 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const chunkSize = 2097152; // 2MB chunks for reading the file for MD5
    const spark = new SparkMD5.ArrayBuffer();
    const fileReader = new FileReader();
    let currentChunk = 0;
    const chunks = Math.ceil(file.size / chunkSize);

    fileReader.onload = (e) => {
      if (e.target?.result) {
        spark.append(e.target.result as ArrayBuffer);
        currentChunk++;
        if (currentChunk < chunks) {
          loadNext();
        } else {
          resolve(spark.end());
        }
      } else {
        reject(new Error("File reading failed for MD5 calculation"));
      }
    };

    fileReader.onerror = () => {
      reject(new Error("File reading error for MD5 calculation"));
    };

    function loadNext() {
      const start = currentChunk * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      fileReader.readAsArrayBuffer(file.slice(start, end));
    }

    loadNext();
  });
};


interface UploadButtonProps {
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  disabled: boolean;
}

const UploadButton = ({ onFileChange, disabled }: UploadButtonProps) => {
  return (
    <label className={`flex items-center gap-2 cursor-pointer bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition shadow-lg ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          d="M12 16V4M12 4L8 8M12 4l4 4M20 16.58A5 5 0 0 1 18 21H6a5 5 0 0 1-2-9.58"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span>Upload PDF</span>
      <input
        type="file"
        accept="application/pdf"
        className="hidden"
        multiple={false}
        onChange={onFileChange}
        disabled={disabled}
      />
    </label>
  )
}

interface UploadCardProps {
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  isUploading: boolean;
}

const UploadCard = ({ onFileChange, isUploading }: UploadCardProps) => {
  return (
    <div className="bg-white rounded-lg p-4 shadow-md w-full max-w-md">
      <p className="font-bold text-2xl text-center mb-4">Upload Reference PDF</p>
      <div className="w-full flex justify-center items-center p-5">
        <UploadButton onFileChange={onFileChange} disabled={isUploading} />
      </div>
    </div>
  )
}

// Define props for UploadPage
interface UploadPageProps {
  PDFmd5sum: string | null;
  setPDFmd5sum: (value: string | null) => void;
  uploaded: boolean;
  setUploaded: (value: boolean) => void;
}

const UploadPage = ({ PDFmd5sum, setPDFmd5sum, uploaded, setUploaded }: UploadPageProps) => {
  // Local state for UI within UploadPage
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);


  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    const inputElement = event.target; 

    if (!file) {
      setError("No file selected.");
      if (inputElement) inputElement.value = ''; 
      return;
    }

    if (file.type !== "application/pdf") {
      setError("Please select a PDF file.");
      if (inputElement) inputElement.value = '';
      return;
    }

    if (file.size > MAX_TOTAL_FILE_SIZE) {
      setError(`File is too large. Maximum size is ${MAX_TOTAL_FILE_SIZE / (1024 * 1024)}MB.`);
      if (inputElement) inputElement.value = '';
      return;
    }

    setIsUploading(true);
    setUploaded(false); // Use prop setter
    setError(null);
    setUploadProgress(0);
    setPDFmd5sum(null); // Use prop setter
    setFileName(file.name);

    try {
      console.log("Calculating MD5 sum...");
      const md5sum = await calculateMD5(file);
      setPDFmd5sum(md5sum); // Use prop setter
      console.log("MD5 sum:", md5sum);

      const targetFilename = `${md5sum}.pdf`;
      const totalChunks = Math.ceil(file.size / UPLOAD_CHUNK_SIZE);
      console.log(`Starting upload of ${file.name} as ${targetFilename} in ${totalChunks} chunks.`);

      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        const start = chunkIndex * UPLOAD_CHUNK_SIZE;
        const end = Math.min(start + UPLOAD_CHUNK_SIZE, file.size);
        const chunk = file.slice(start, end);

        const formData = new FormData();
        formData.append('file_chunk', chunk, file.name); 
        formData.append('filename', targetFilename);
        formData.append('chunk_number', chunkIndex.toString());
        formData.append('total_chunks', totalChunks.toString());

        console.log(`Uploading chunk ${chunkIndex + 1}/${totalChunks}...`);
        const response = await fetch(`${BACKEND_URL}/upload_chunk`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: "Unknown error during chunk upload." }));
          throw new Error(errorData.detail || `Chunk ${chunkIndex + 1} upload failed: ${response.statusText}`);
        }

        const progress = Math.round(((chunkIndex + 1) / totalChunks) * 100);
        setUploadProgress(progress);
        console.log(`Chunk ${chunkIndex + 1} uploaded. Progress: ${progress}%`);
      }

      setUploaded(true); // Use prop setter
      console.log("File upload completed successfully.");

    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.message || "An error occurred during upload.");
      setPDFmd5sum(null); // Use prop setter
      setUploaded(false); // Use prop setter
    } finally {
      setIsUploading(false);
      if (inputElement) inputElement.value = ''; 
      console.log("Upload process finished.");
    }
  };

  return (
    <div className="max-h-screen h-screen max-w-screen w-screen bg-gray-900 flex flex-col items-center justify-center p-6 space-y-4">
      <UploadCard onFileChange={handleFileChange} isUploading={isUploading} />

      {fileName && !isUploading && !error && (
        <div className="text-sm text-gray-300">
            Selected file: {fileName}
        </div>
      )}

      {/* Display PDFmd5sum from props */}
      {PDFmd5sum && !isUploading && !error && !uploaded && (
        <div className="text-sm text-gray-300">
            Calculated PDF MD5: {PDFmd5sum}
        </div>
      )}

      {isUploading && (
        <div className="w-full max-w-md text-center">
          <div className="text-white mb-1">Uploading {fileName}... {uploadProgress}%</div>
          <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
            <div
              className="bg-blue-600 h-2.5 rounded-full"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
        </div>
      )}
      {/* The success message is now handled by the Home component based on the 'uploaded' prop */}
      {error && (
        <div className="mt-2 text-red-300 bg-red-800 p-3 rounded-md shadow">
          Error: {error}
        </div>
      )}
    </div>
  );
}

export default UploadPage;