import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
interface QueryPageProps {
  PDFmd5sum: string | null;
}

const QueryPage = ({PDFmd5sum}: QueryPageProps) => {
    const [query, setQuery] = useState<string>("");
    const [submitted, setSubmitted] = useState<boolean>(false);
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
                    />
                    <button
                        onClick={() => setSubmitted(!submitted)}
                        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                    >
                        Submit Query
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
                                <p>Content for Vanilla RAG</p>
                            </TabsContent>
                            <TabsContent value="self-query">
                                <p>Content for Self Query RAG</p>
                            </TabsContent>
                            <TabsContent value="reranker">
                                <p>Content for Reranker RAG</p>
                            </TabsContent>
                        </Tabs>
                    </div>
                )}
            </div>
        </div>
    );
}

export default QueryPage;