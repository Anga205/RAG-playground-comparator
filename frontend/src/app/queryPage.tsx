import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area"
import {
    Carousel,
    CarouselContent,
    CarouselItem,
    CarouselNext,
    CarouselPrevious,
} from "@/components/ui/carousel"

interface PipelineCarouselProps {
    data: Record<string, any>;
}

const BACKEND_URL =
  process.env.NODE_ENV === "development" || process.env["dev"]
    ? "http://localhost:8000"
    : "https://api-rag.anga.codes";

const PipelineCarousel = ({ data }: PipelineCarouselProps) => {
    return (
        <Carousel className="w-full max-w-4xl" opts={{ loop: true }}>
            <CarouselContent>
                {Object.entries(data).map(([key, value], index) => (
                    <CarouselItem key={index} className="md:basis-full">
                        <div className="p-4 rounded-lg bg-gray-100 dark:bg-gray-800">
                            <h3 className="font-semibold mb-2 text-center text-2xl">{key.charAt(0).toUpperCase() + key.slice(1)}</h3>
                            <ScrollArea className="h-80 w-full">
                                {value === null ? (
                                    <p className="text-sm dark:text-gray-400">Loading, Please wait for upto a minute</p>
                                ) : typeof value === "string" ? (
                                    <p className="text-sm dark:text-gray-400">{value}</p>
                                ) : (
                                    <pre className="bg-gray-900 text-green-400 rounded p-2 overflow-x-auto text-xs">
                                        <code>
                                            {JSON.stringify(value, null, 2)}
                                        </code>
                                    </pre>
                                )}
                            </ScrollArea>
                        </div>
                    </CarouselItem>
                ))}
            </CarouselContent>
            <CarouselPrevious />
            <CarouselNext />
        </Carousel>
    );
}

const QueryPage = () => {
    const [query, setQuery] = useState<string>("");
    const [submitted, setSubmitted] = useState<boolean>(false);
    const [VanillaRAG, setVanillaRAG] = useState<{}>({ "answer": null, "chunks": null });
    const [SelfQueryRAG, setSelfQueryRAG] = useState<{}>({ "answer": null, "refined_query": null, "chunks": null });
    const [RerankerRAG, setRerankerRAG] = useState<{}>({ "answer": null, "chunks": null, "ranked_chunks": null });
    const [loading, setLoading] = useState<boolean>(false);

    const handleSubmit = async () => {
        if (!query.trim()) return;
        setSubmitted(true);
        setLoading(true);

        // Set loading state for each pipeline
        setVanillaRAG({ "answer": null, "chunks": null });
        setSelfQueryRAG({ "answer": null, "refined_query": null, "chunks": null });
        setRerankerRAG({ "answer": null, "chunks": null, "ranked_chunks": null });

        // Helper to fetch and set state for each pipeline
        const fetchAndSet = async (
            url: string,
            setter: React.Dispatch<React.SetStateAction<any>>
        ) => {
            try {
                const res = await fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query }),
                });
                const data = await res.json();
                setter(data);
            } catch {
                setter({ error: "Failed to fetch" });
            }
        };

        // Start all fetches in parallel, but update state as soon as each returns
        fetchAndSet(`${BACKEND_URL}/simple-rag`, setVanillaRAG);
        fetchAndSet(`${BACKEND_URL}/self-query`, setSelfQueryRAG);
        fetchAndSet(`${BACKEND_URL}/reranker`, setRerankerRAG);

        // Wait for all to finish before disabling loading
        Promise.all([
            fetch(`${BACKEND_URL}/simple-rag`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query }),
            }),
            fetch(`${BACKEND_URL}/self-query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query }),
            }),
            fetch(`${BACKEND_URL}/reranker`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query }),
            }),
        ]).finally(() => setLoading(false));
    };

    return (
        <div className="flex justify-center items-center h-screen max-h-screen w-screen max-w-screen bg-gray-900 p-20">
            <div className={`bg-white rounded-lg p-4 shadow-md ${submitted ? 'w-full h-full' : 'max-w-md'}`}>
                <p className="font-bold text-2xl text-center mb-2">Query The LLM</p>
                <p className='text-sm px-3 text-center'>Enter a query here to ask the LLM, it will then show you responses from all 3 RAG pipelines at the same time</p>
                <div className="w-full flex justify-center items-center p-5 space-x-3">
                    <textarea
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Type your question here..."
                        className="w-full p-2 border border-gray-300 rounded"
                        disabled={loading}
                    />
                    <button
                        onClick={handleSubmit}
                        className={`bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 ${!query.trim() || loading ? "opacity-50 cursor-not-allowed" : ""}`}
                        disabled={!query.trim() || loading}
                    >
                        {loading ? "Loading..." : "Submit Query"}
                    </button>
                </div>
                {submitted && (
                    <div className="w-full justify-center h-full">
                        <Tabs defaultValue="vanilla">
                            <TabsList className='w-full'>
                                <TabsTrigger value="vanilla">Vanilla RAG</TabsTrigger>
                                <TabsTrigger value="self-query">Self Query RAG</TabsTrigger>
                                <TabsTrigger value="reranker">Reranker RAG</TabsTrigger>
                            </TabsList>
                            <TabsContent value="vanilla" className='w-full flex justify-center items-center'>
                                <PipelineCarousel data={VanillaRAG} />
                            </TabsContent>
                            <TabsContent value="self-query" className='w-full flex justify-center items-center'>
                                <PipelineCarousel data={SelfQueryRAG} />
                            </TabsContent>
                            <TabsContent value="reranker" className='w-full flex justify-center items-center'>
                                <PipelineCarousel data={RerankerRAG} />
                            </TabsContent>
                        </Tabs>
                    </div>
                )}
            </div>
        </div>
    );
}

export default QueryPage;