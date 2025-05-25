"use client";
import { useRef, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { BookOpen, Search, Layers, UploadCloud } from "lucide-react";

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

function UploadPDF() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleButtonClick = () => {
    inputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setMessage(null);

    if (!file) return;
    if (file.type !== "application/pdf") {
      setMessage("Only PDF files are allowed.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setMessage("File size exceeds 100MB limit.");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        setMessage("Upload successful!");
      } else {
        setMessage("Upload failed.");
      }
    } catch {
      setMessage("Upload failed.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
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
        className="flex items-center bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded mb-2"
        onClick={handleButtonClick}
        disabled={uploading}
        type="button"
      >
        <UploadCloud className="mr-2 w-5 h-5" />
        {uploading ? "Uploading..." : "Upload PDF"}
      </button>
      {message && (
        <div className="text-sm text-center text-red-600">{message}</div>
      )}
    </div>
  );
}

function SimpleRagDemo() {
  return (
    <div>
      <h2 className="text-lg font-semibold mb-2">Simple RAG Demo</h2>
      <p className="mb-2 text-gray-700">
        This demo shows a basic Retrieval-Augmented Generation workflow: retrieve relevant documents and generate an answer.
      </p>
      {/* Add your simple RAG demo UI here */}
      <input
        className="border rounded px-3 py-2 w-full mb-2"
        placeholder="Ask a question..."
      />
      <button className="bg-blue-600 text-white px-4 py-2 rounded">Run</button>
    </div>
  );
}

function SelfQueryDemo() {
  return (
    <div>
      <h2 className="text-lg font-semibold mb-2">Self Query RAG Demo</h2>
      <p className="mb-2 text-gray-700">
        This demo uses a self-query retriever to interpret your question and retrieve documents more intelligently.
      </p>
      {/* Add your self-query demo UI here */}
      <input
        className="border rounded px-3 py-2 w-full mb-2"
        placeholder="Ask a question..."
      />
      <button className="bg-green-600 text-white px-4 py-2 rounded">Run</button>
    </div>
  );
}

function RerankerDemo() {
  return (
    <div>
      <h2 className="text-lg font-semibold mb-2">Reranker RAG Demo</h2>
      <p className="mb-2 text-gray-700">
        This demo retrieves documents and then reranks them before generating an answer.
      </p>
      {/* Add your reranker demo UI here */}
      <input
        className="border rounded px-3 py-2 w-full mb-2"
        placeholder="Ask a question..."
      />
      <button className="bg-purple-600 text-white px-4 py-2 rounded">Run</button>
    </div>
  );
}

export default function Home() {
  return (
    <div className="h-screen w-screen bg-gray-900 flex items-center justify-center p-6">
      <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-md">
        <UploadPDF />
        <Tabs defaultValue="simple-rag">
          <TabsList className="grid w-full grid-cols-3 mb-4">
            <TabsTrigger value="simple-rag">
              <BookOpen className="inline-block mr-2 w-4 h-4" />
              Simple RAG
            </TabsTrigger>
            <TabsTrigger value="self-query">
              <Search className="inline-block mr-2 w-4 h-4" />
              Self Query
            </TabsTrigger>
            <TabsTrigger value="reranker">
              <Layers className="inline-block mr-2 w-4 h-4" />
              Reranker
            </TabsTrigger>
          </TabsList>
          <TabsContent value="simple-rag">
            <SimpleRagDemo />
          </TabsContent>
          <TabsContent value="self-query">
            <SelfQueryDemo />
          </TabsContent>
          <TabsContent value="reranker">
            <RerankerDemo />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
