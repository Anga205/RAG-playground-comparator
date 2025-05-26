"use client";
import { use, useState } from 'react';
import UploadPage from './uploadPage';
import QueryPage from './queryPage';

const Home = () => {
    const [PDFmd5sum, setPDFmd5sum] = useState<string | null>(null);
    const [uploaded, setUploaded] = useState<boolean>(false);

    return (
        uploaded ? 
            <QueryPage 
                PDFmd5sum={PDFmd5sum}
            />:
            <UploadPage
                PDFmd5sum={PDFmd5sum}
                setPDFmd5sum={setPDFmd5sum}
                uploaded={uploaded}
                setUploaded={setUploaded}
            />
    )
}

export default Home;