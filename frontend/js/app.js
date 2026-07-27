document.addEventListener('DOMContentLoaded', () => {
    // Generate or fetch Session ID
    let sessionId = localStorage.getItem('gsstb_session_id');
    if (!sessionId) {
        sessionId = 'session_' + Math.random().toString(36).substring(2, 9);
        localStorage.setItem('gsstb_session_id', sessionId);
    }

    // DOM Elements
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const filterStd = document.getElementById('filter-std');
    const filterSubject = document.getElementById('filter-subject');
    const booksList = document.getElementById('books-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const statDocs = document.getElementById('stat-docs');
    const statChunks = document.getElementById('stat-chunks');

    // Modals
    const uploadModal = document.getElementById('upload-modal');
    const uploadModalBtn = document.getElementById('upload-modal-btn');
    const closeModalBtn = document.querySelector('.close-modal');
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadProgress = document.getElementById('upload-progress');

    const citationModal = document.getElementById('citation-modal');
    const closeCitationModalBtn = document.querySelector('.close-citation-modal');
    const citationModalBody = document.getElementById('citation-modal-body');

    // Load indexed documents on startup
    loadDocuments();

    // Event Listeners
    uploadModalBtn.addEventListener('click', () => uploadModal.classList.add('active'));
    closeModalBtn.addEventListener('click', () => uploadModal.classList.remove('active'));
    closeCitationModalBtn.addEventListener('click', () => citationModal.classList.remove('active'));

    newChatBtn.addEventListener('click', async () => {
        try {
            await fetch(`/api/chat/${sessionId}`, { method: 'DELETE' });
            sessionId = 'session_' + Math.random().toString(36).substring(2, 9);
            localStorage.setItem('gsstb_session_id', sessionId);
            chatMessages.innerHTML = `
                <div class="welcome-card glass-panel">
                    <div class="welcome-icon"><i class="fa-solid fa-chalkboard-user"></i></div>
                    <h2>Conversation Memory Cleared</h2>
                    <p>Start a new conversation by asking any question from GSSTB textbooks.</p>
                </div>
            `;
        } catch (err) {
            console.error('Error clearing session:', err);
        }
    });

    // File Drop Zone Upload
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary)';
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--border-color)';
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border-color)';
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    async function handleFileUpload(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            alert('Please select a valid PDF file.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        dropZone.classList.add('hidden');
        uploadProgress.classList.remove('hidden');

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const responseText = await res.text();
            let data;
            try {
                data = JSON.parse(responseText);
            } catch (jsonErr) {
                throw new Error(`Server returned status ${res.status}: ${responseText || 'Empty response'}`);
            }

            if (!res.ok) {
                throw new Error(data.detail || `Upload failed with status ${res.status}`);
            }

            alert(`Success: ${data.message}\nBook: ${data.book_name}\nPages: ${data.pages_processed}\nChunks: ${data.chunks_created}`);
            uploadModal.classList.remove('active');
            loadDocuments();
        } catch (err) {
            alert('Upload Error: ' + err.message);
        } finally {
            dropZone.classList.remove('hidden');
            uploadProgress.classList.add('hidden');
            fileInput.value = '';
        }
    }

    async function loadDocuments() {
        try {
            const res = await fetch('/api/documents');
            const books = await res.json();

            let totalChunks = 0;
            if (!books.length) {
                booksList.innerHTML = `<div class="welcome-card" style="padding:1rem;margin:0;font-size:0.8rem;">No textbooks indexed yet. Click + to upload GSSTB PDFs.</div>`;
                statDocs.innerHTML = `<i class="fa-solid fa-book"></i> 0 Books`;
                statChunks.innerHTML = `<i class="fa-solid fa-cubes"></i> 0 Chunks`;
                return;
            }

            booksList.innerHTML = '';
            books.forEach(b => {
                totalChunks += b.chunk_count;
                const card = document.createElement('div');
                card.className = 'book-card';
                card.innerHTML = `
                    <div class="book-info">
                        <h4>${b.book_name}</h4>
                        <div class="book-meta">
                            <span class="tag">${b.standard}</span>
                            <span class="tag">${b.subject}</span>
                            <span class="tag">${b.total_pages} Pages</span>
                        </div>
                    </div>
                    <button class="delete-book-btn" title="Delete Book" onclick="deleteBook('${b.book_name}')">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                `;
                booksList.appendChild(card);
            });

            statDocs.innerHTML = `<i class="fa-solid fa-book"></i> ${books.length} Books`;
            statChunks.innerHTML = `<i class="fa-solid fa-cubes"></i> ${totalChunks} Chunks`;
        } catch (err) {
            console.error('Error loading documents:', err);
        }
    }

    window.deleteBook = async function(bookName) {
        if (!confirm(`Are you sure you want to delete textbook "${bookName}"?`)) return;
        try {
            await fetch(`/api/documents/${encodeURIComponent(bookName)}`, { method: 'DELETE' });
            loadDocuments();
        } catch (err) {
            alert('Delete Error: ' + err.message);
        }
    };

    window.useSampleQuery = function(text) {
        chatInput.value = text;
        chatForm.dispatchEvent(new Event('submit'));
    };

    // Chat Submission
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userMsg = chatInput.value.trim();
        if (!userMsg) return;

        // Append User Message
        appendMessage('user', userMsg);
        chatInput.value = '';

        // Add loading assistant bubble
        const loadingId = 'loading_' + Date.now();
        appendLoadingBubble(loadingId);

        try {
            const payload = {
                message: userMsg,
                session_id: sessionId,
                standard_filter: filterStd.value || null,
                subject_filter: filterSubject.value || null
            };

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            removeLoadingBubble(loadingId);

            appendMessage('assistant', data.answer, data.citations);
        } catch (err) {
            removeLoadingBubble(loadingId);
            appendMessage('assistant', 'Error connecting to RAG server: ' + err.message);
        }
    });

    function appendMessage(role, text, citations = []) {
        // Remove welcome card if present
        const welcomeCard = document.querySelector('.welcome-card');
        if (welcomeCard && chatMessages.children.length === 1) {
            welcomeCard.remove();
        }

        const row = document.createElement('div');
        row.className = `message-row ${role}`;

        const avatarIcon = role === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

        let citationsHtml = '';
        if (citations && citations.length > 0) {
            citationsHtml = `
                <div class="citation-container">
                    <div class="citation-title"><i class="fa-solid fa-bookmark"></i> Source Citations:</div>
                    ${citations.map((c, i) => `
                        <span class="citation-chip" onclick='openCitationModal(${JSON.stringify(c)})'>
                            <i class="fa-solid fa-file-lines"></i> ${c.book_name} | Page ${c.page_number}
                        </span>
                    `).join('')}
                </div>
            `;
        }

        row.innerHTML = `
            <div class="message-avatar">${avatarIcon}</div>
            <div class="message-bubble">
                <div class="message-text">${formatMarkdown(text)}</div>
                ${citationsHtml}
            </div>
        `;

        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendLoadingBubble(id) {
        const row = document.createElement('div');
        row.className = 'message-row assistant';
        row.id = id;
        row.innerHTML = `
            <div class="message-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-bubble">
                <i class="fa-solid fa-circle-notch fa-spin"></i> Searching textbook knowledge base & generating answer...
            </div>
        `;
        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeLoadingBubble(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    window.openCitationModal = function(citation) {
        citationModalBody.innerHTML = `
            <div class="snippet-card">
                <div class="snippet-header">
                    <span>Book: ${citation.book_name}</span>
                    <span>Page: ${citation.page_number} (${citation.standard || ''} ${citation.subject || ''})</span>
                </div>
                <div class="snippet-text">${escapeHtml(citation.relevant_text)}</div>
            </div>
        `;
        citationModal.classList.add('active');
    };

    function formatMarkdown(str) {
        return escapeHtml(str).replace(/\n/g, '<br>');
    }

    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
