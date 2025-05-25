"use client";

import { useRef, useState, FormEvent } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"; // Assuming you have these from ShadCN or similar
import { BookOpen, Search, Layers, UploadCloud, Loader2, AlertCircle, FileText, Clock } from "lucide-react";

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
const BACKEND_URL = "http://localhost:8000";

type RagType = "simple" | "self_query" | "reranker";

interface RetrievedContextChunk {
  id: string;
  score: number | null;
  text: string;
  page_number: number | null;
  source_filename: string | null;
  start_index: number | null;
}

interface QueryResponse {
  answer: string;
  retrieved_context: RetrievedContextChunk[];
  response_time_seconds: number;
  rag_type_used: RagType;
  query_used_for_retrieval: string;
}

interface UploadSuccessResponse {
  message: string;
  file_id: string;
  original_filename: string;
  num_pages_extracted: number;
  num_chunks_created: number;
}

function UploadPDF({ 
  onUploadSuccess,
  setGlobalError 
}: { 
  onUploadSuccess: (fileId: string, filename: string) => void,
  setGlobalError: (message: string | null) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleButtonClick = () => {
    inputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setUploadMessage(null);
    setUploadError(null);
    setGlobalError(null);

    if (!file) return;
    if (file.type !== "application/pdf") {
      setUploadError("Only PDF files are allowed.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setUploadError("File size exceeds 100MB limit.");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${BACKEND_URL}/upload`, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();

      if (res.ok) {
        const successData = data as UploadSuccessResponse;
        setUploadMessage(`Successfully processed "${successData.original_filename}". Chunks: ${successData.num_chunks_created}. File ID: ${successData.file_id}`);
        onUploadSuccess(successData.file_id, successData.original_filename);
      } else {
        setUploadError(data.detail || "Upload failed. Check server logs.");
        setGlobalError(data.detail || "Upload failed. Check server logs.");
      }
    } catch (err) {
      console.error("Upload error:", err);
      const errorMsg = err instanceof Error ? err.message : "An unknown error occurred during upload.";
      setUploadError(`Upload failed: ${errorMsg}`);
      setGlobalError(`Upload failed: ${errorMsg}`);
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = ""; // Reset file input
    }
  };

  return (
    <div className="mb-4">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      <button
        className="w-full flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded mb-2 transition-colors duration-150"
        onClick={handleButtonClick}
        disabled={isUploading}
        type="button"
      >
        {isUploading ? (
          <Loader2 className="mr-2 w-5 h-5 animate-spin" />
        ) : (
          <UploadCloud className="mr-2 w-5 h-5" />
        )}
        {isUploading ? "Uploading & Processing..." : "Upload & Process PDF"}
      </button>
      {uploadMessage && (
        <div className="text-sm text-center text-green-600 bg-green-100 p-2 rounded">{uploadMessage}</div>
      )}
      {uploadError && (
        <div className="text-sm text-center text-red-600 bg-red-100 p-2 rounded">{uploadError}</div>
      )}
    </div>
  );
}

interface RagDemoProps {
  ragType: RagType;
  fileId: string | null;
  uploadedFilename: string | null;
  setGlobalError: (message: string | null) => void;
}

function RagQuerySection({ ragType, fileId, uploadedFilename, setGlobalError }: RagDemoProps) {
  const [query, setQuery] = useState("");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);

  const handleQuerySubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!fileId) {
      setQueryError("Please upload and process a PDF file first.");
      setGlobalError("Please upload and process a PDF file first.");
      return;
    }
    if (!query.trim()) {
      setQueryError("Please enter a question.");
      return;
    }

    setIsQuerying(true);
    setQueryError(null);
    setQueryResult(null);
    setGlobalError(null);

    try {
      const res = await fetch(`${BACKEND_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, rag_type: ragType, file_id: fileId }),
      });
      const data = await res.json();
      if (res.ok) {
        setQueryResult(data as QueryResponse);
      } else {
        setQueryError(data.detail || `Query failed for ${ragType}.`);
        setGlobalError(data.detail || `Query failed for ${ragType}.`);
      }
    } catch (err) {
      console.error(`Query error (${ragType}):`, err);
      const errorMsg = err instanceof Error ? err.message : "An unknown error occurred.";
      setQueryError(`Query failed: ${errorMsg}`);
      setGlobalError(`Query failed: ${errorMsg}`);
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className="mt-4">
      <form onSubmit={handleQuerySubmit}>
        <textarea
          className="border rounded px-3 py-2 w-full mb-2 h-24 resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          placeholder={`Ask a question to "${uploadedFilename || 'your uploaded PDF'}" using ${ragType.replace('_', ' ')} RAG...`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={!fileId || isQuerying}
        />
        <button
          type="submit"
          className="w-full flex items-center justify-center bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded transition-colors duration-150"
          disabled={!fileId || isQuerying || !query.trim()}
        >
          {isQuerying ? (
            <Loader2 className="mr-2 w-5 h-5 animate-spin" />
          ) : (
            <Search className="mr-2 w-5 h-5" />
          )}
          {isQuerying ? "Searching..." : `Ask with ${ragType.replace('_', ' ')} RAG`}
        </button>
      </form>

      {queryError && (
        <div className="mt-4 text-sm text-red-600 bg-red-100 p-3 rounded">
          <AlertCircle className="inline mr-2 h-5 w-5" />
          {queryError}
        </div>
      )}

      {isQuerying && (
        <div className="mt-6 flex flex-col items-center justify-center text-gray-600">
          <Loader2 className="w-10 h-10 animate-spin mb-2" />
          <p>Searching for answers...</p>
        </div>
      )}

      {queryResult && (
        <div className="mt-6 space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-1">Answer:</h3>
            <p className="bg-gray-100 p-3 rounded text-gray-700 whitespace-pre-wrap">{queryResult.answer}</p>
          </div>
          
          {queryResult.query_used_for_retrieval && queryResult.query_used_for_retrieval.toLowerCase() !== query.toLowerCase() && (
             <div>
                <h4 className="text-md font-medium text-gray-600">Query used for retrieval:</h4>
                <p className="text-sm text-gray-500 italic p-2 bg-yellow-50 rounded">"{queryResult.query_used_for_retrieval}"</p>
            </div>
          )}

          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Retrieved Context Chunks ({queryResult.retrieved_context.length}):</h3>
            {queryResult.retrieved_context.length > 0 ? (
              <div className="space-y-3 max-h-96 overflow-y-auto p-2 border rounded bg-white">
                {queryResult.retrieved_context.map((chunk, index) => (
                  <div key={chunk.id || index} className="p-3 border rounded-md bg-gray-50 shadow-sm">
                    <p className="text-sm text-gray-700 leading-relaxed">{chunk.text}</p>
                    <div className="mt-2 text-xs text-gray-500 flex flex-wrap gap-x-3 gap-y-1">
                      <span>ID: {chunk.id ? chunk.id.substring(0,8) + '...' : 'N/A'}</span>
                      {chunk.score !== null && <span>Score: {chunk.score.toFixed(4)}</span>}
                      {chunk.page_number && <span>Page: {chunk.page_number}</span>}
                      {chunk.source_filename && <span>Source: {chunk.source_filename}</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-600">No context chunks were retrieved.</p>
            )}
          </div>
          
          <div className="text-sm text-gray-500 flex items-center">
            <Clock className="w-4 h-4 mr-1" />
            <span>Response Time: {queryResult.response_time_seconds} seconds</span>
          </div>
        </div>
      )}
    </div>
  );
}


export default function Home() {
  const [fileId, setFileId] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null); // For errors not specific to upload/query

  const handleUploadSuccess = (newFileId: string, filename: string) => {
    setFileId(newFileId);
    setUploadedFilename(filename);
    setGlobalError(null); // Clear global error on new upload
  };

  return (
    <div className="min-h-screen w-screen bg-gray-100 flex flex-col items-center p-4 sm:p-6">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl">
        <header className="mb-6 text-center">
          <h1 className="text-3xl font-bold text-gray-800">RAG Playground</h1>
          <p className="text-gray-600">Upload a PDF and query its content using different RAG strategies.</p>
        </header>
        
        <UploadPDF onUploadSuccess={handleUploadSuccess} setGlobalError={setGlobalError} />

        {globalError && (
           <div className="my-4 text-sm text-center text-red-700 bg-red-100 p-3 rounded-md">
             <AlertCircle className="inline mr-2 h-5 w-5" />
             <strong>Global Error:</strong> {globalError}
           </div>
        )}

        {fileId && (
          <Tabs defaultValue="simple" className="w-full mt-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="simple" className="flex items-center justify-center data-[state=active]:bg-blue-100 data-[state=active]:text-blue-700 data-[state=active]:shadow-sm">
                <BookOpen className="mr-2 w-4 h-4" /> Simple RAG
              </TabsTrigger>
              <TabsTrigger value="self_query" className="flex items-center justify-center data-[state=active]:bg-blue-100 data-[state=active]:text-blue-700 data-[state=active]:shadow-sm">
                <Search className="mr-2 w-4 h-4" /> Self-Query
              </TabsTrigger>
              <TabsTrigger value="reranker" className="flex items-center justify-center data-[state=active]:bg-blue-100 data-[state=active]:text-blue-700 data-[state=active]:shadow-sm">
                <Layers className="mr-2 w-4 h-4" /> Reranker
              </TabsTrigger>
            </TabsList>
            <TabsContent value="simple" className="pt-4">
              <RagQuerySection ragType="simple" fileId={fileId} uploadedFilename={uploadedFilename} setGlobalError={setGlobalError} />
            </TabsContent>
            <TabsContent value="self_query" className="pt-4">
              <RagQuerySection ragType="self_query" fileId={fileId} uploadedFilename={uploadedFilename} setGlobalError={setGlobalError} />
            </TabsContent>
            <TabsContent value="reranker" className="pt-4">
              <RagQuerySection ragType="reranker" fileId={fileId} uploadedFilename={uploadedFilename} setGlobalError={setGlobalError} />
            </TabsContent>
          </Tabs>
        )}
      </div>
      <footer className="mt-8 text-center text-sm text-gray-500">
        <p>RAG Playground Comparator - 2025</p>
      </footer>
    </div>
  );
}
