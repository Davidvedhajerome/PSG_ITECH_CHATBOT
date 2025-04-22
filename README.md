# PSG iTech College Chatbot

An AI-powered chatbot for PSG Institute of Technology and Applied Research that can answer questions about admissions, programs, facilities, and more.

## Features

- Real-time chat interface
- Answers questions about:
  - Admission process
  - Programs offered
  - Hostel facilities
  - Placements
  - Campus facilities
  - Research opportunities
  - Contact information
  - And more!

## Prerequisites

- Python 3.8+
- OpenAI API key

## Setup

1. Navigate to the project directory:
```bash
cd E:\psg-itech-chatbot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

4. Run the data scraper to collect college information:
```bash
python scrape_data.py
```

5. Start the FastAPI server:
```bash
uvicorn app:app --reload
```

6. Open your browser and navigate to `http://localhost:8000` to use the chatbot.

## Usage

Simply type your question in the chat interface and press Enter or click Send. The chatbot will respond with relevant information about PSG iTech.

Example questions:
- What programs are offered at PSG iTech?
- Tell me about the admission process
- What are the hostel facilities available?
- How can I contact the college?
- What research facilities are available?

## Project Structure

```
E:\psg-itech-chatbot\
├── app.py                 # Main FastAPI application
├── scrape_data.py        # Web scraper for college data
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── college_data.json     # Scraped college data
├── templates/
│   └── index.html       # Chat interface template
└── static/              # Static files (if needed)
```

## Technology Stack

- Backend: FastAPI
- Frontend: HTML, TailwindCSS, JavaScript
- AI: OpenAI GPT, LangChain
- Vector Store: Chroma
- Data Processing: BeautifulSoup4

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. "# PSG_ITECH_CHATBOT" 
