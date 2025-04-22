import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Any
import os
import PyPDF2
from io import BytesIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_pdf_content(pdf_content: bytes) -> str:
    """Extract text content from PDF bytes"""
    try:
        pdf_file = BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return clean_text(text)
    except Exception as e:
        logger.error(f"Error extracting PDF content: {str(e)}")
        return ""

def process_cutoff_pdf(content: str, url: str) -> Dict[str, Any]:
    """Process cut-off PDF content"""
    data = {
        "type": "cutoff_pdf",
        "url": url,
        "filename": url.split('/')[-1],
        "content": content,
        "parsed_data": {}
    }
    
    # Extract year from filename
    year_match = re.search(r'(\d{4}-\d{4})', url)
    if year_match:
        data["academic_year"] = year_match.group(1)
    
    # Try to extract cut-off marks
    lines = content.split('\n')
    for line in lines:
        # Look for patterns like "Branch: XXXX, Cut-off: YYYY"
        branch_match = re.search(r'Branch:\s*([^,]+)', line)
        cutoff_match = re.search(r'Cut-off:\s*(\d+(?:\.\d+)?)', line)
        
        if branch_match and cutoff_match:
            branch = clean_text(branch_match.group(1))
            cutoff = float(cutoff_match.group(1))
            data["parsed_data"][branch] = cutoff
    
    return data

def scrape_url(url: str) -> Dict[str, Any]:
    """Scrape data from a given URL"""
    try:
        response = requests.get(url, timeout=30)
        if url.lower().endswith('.pdf'):
            content = extract_pdf_content(response.content)
            if 'cut_off' in url.lower():
                return process_cutoff_pdf(content, url)
            return {
                "content": content, 
                "type": "pdf",
                "url": url,
                "filename": url.split('/')[-1]
            }
        elif url.lower().endswith('.docx'):
            # Store the DOCX file path for later processing
            return {
                "content": "DOCX file available", 
                "type": "docx",
                "url": url,
                "filename": url.split('/')[-1]
            }
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            data = extract_page_data(soup, url)
            data["url"] = url
            return data
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return {
            "error": str(e),
            "type": "error",
            "url": url
        }

def process_cutoff_data(soup: BeautifulSoup) -> Dict[str, Any]:
    """Process cut-off related data from the page"""
    cutoff_data = {
        "be_btech": [],
        "barch": [],
        "latest_cutoff": {}
    }
    
    tables = soup.find_all('table')
    for table in tables:
        caption = table.find_previous('h1') or table.find_previous('h2')
        table_type = "be_btech" if "B.E" in str(caption) else "barch" if "B.Arch" in str(caption) else None
        
        if table_type:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['th', 'td'])
                if cols:
                    year = clean_text(cols[0].get_text())
                    link = cols[1].find('a')
                    if link:
                        entry = {
                            "academic_year": year,
                            "pdf_url": link['href'],
                            "file_name": link['href'].split('/')[-1]
                        }
                        cutoff_data[table_type].append(entry)
                        
                        # Store latest cutoff
                        if "2024" in year:
                            cutoff_data["latest_cutoff"][table_type] = entry
    
    return cutoff_data

def extract_page_data(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """Extract relevant data from a BeautifulSoup object"""
    data = {
        "title": "",
        "content": "",
        "metadata": {},
        "type": "html"
    }
    
    # Extract title
    title_tag = soup.find('title')
    if title_tag:
        data["title"] = clean_text(title_tag.text)
    
    # Extract main content based on URL pattern
    if '/cutt-off' in url:
        data["type"] = "cutoff"
        data["content"] = process_cutoff_data(soup)
            
    elif '/departments/' in url:
        data["type"] = "department"
        dept_content = soup.find('main') or soup.find(class_=re.compile(r'department|content|main'))
        if dept_content:
            data["content"] = clean_text(dept_content.get_text())
            
    elif '/faculty' in url:
        data["type"] = "faculty"
        faculty_list = []
        faculty_items = soup.find_all(class_=re.compile(r'faculty|staff|teacher'))
        for item in faculty_items:
            faculty_list.append(clean_text(item.get_text()))
        data["content"] = faculty_list
        
    elif '/research' in url:
        data["type"] = "research"
        research_content = soup.find('main') or soup.find(class_=re.compile(r'research|content|main'))
        if research_content:
            data["content"] = clean_text(research_content.get_text())
            
    elif '/placements' in url:
        data["type"] = "placements"
        placement_content = soup.find('main') or soup.find(class_=re.compile(r'placement|content|main'))
        if placement_content:
            data["content"] = clean_text(placement_content.get_text())
            
    else:
        # Default content extraction
        main_content = soup.find('main') or soup.find(class_=re.compile(r'content|main'))
        if main_content:
            data["content"] = clean_text(main_content.get_text())
    
    # Extract metadata
    meta_tags = soup.find_all('meta')
    for tag in meta_tags:
        name = tag.get('name', tag.get('property', ''))
        content = tag.get('content', '')
        if name and content:
            data["metadata"][name] = content
    
    return data

def merge_data(existing_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Merge new data with existing data"""
    for key, value in new_data.items():
        if key in existing_data:
            if isinstance(value, list):
                existing_data[key].extend(value)
            elif isinstance(value, dict):
                existing_data[key].update(value)
            else:
                existing_data[key] = value
        else:
            existing_data[key] = value
    return existing_data

def generate_base_college_data() -> Dict[str, Any]:
    """Generate base college information"""
    return {
        "general_info": {
            "name": "PSG Institute of Technology and Applied Research",
            "short_name": "PSG iTech",
            "established": "2014",
            "type": "Private Engineering College",
            "affiliation": "Anna University",
            "approval": "AICTE",
            "accreditation": "NAAC A+ Grade",
            "location": {
                "address": "Avinashi Road, Neelambur",
                "city": "Coimbatore",
                "state": "Tamil Nadu",
                "pincode": "641062",
                "country": "India"
            },
            "contact": {
                "phone": [
                    "0422 3933 666",
                    "+91 8754042807",
                    "+91 8754042808"
                ],
                "email": "principal@psgitech.ac.in",
                "website": "https://psgitech.ac.in"
            },
            "vision": "To achieve excellence in education and research, and nurture engineers with ethics, who will face global challenges to serve industry and society.",
            "mission": [
                "To facilitate active learning and vocational training.",
                "To encourage and promote questioning spirit and 'can-do' entrepreneurial attitude.",
                "To foster industry - institute collaboration.",
                "To ignite passion for creative work and selfless service towards a sustainable world.",
                "To provide intellectually stimulating environment, conducive for research."
            ]
        },
        "academics": {
            "programs": {
                "undergraduate": {
                    "B.E. Artificial Intelligence & Data Science": {
                        "duration": "4 years",
                        "seats": 60,
                        "eligibility": "10+2 with Mathematics, Physics, and Chemistry"
                    },
                    "B.E. Civil Engineering": {
                        "duration": "4 years",
                        "seats": 60,
                        "eligibility": "10+2 with Mathematics, Physics, and Chemistry"
                    },
                    "B.E. Computer Science & Engineering": {
                        "duration": "4 years",
                        "seats": 120,
                        "eligibility": "10+2 with Mathematics, Physics, and Chemistry"
                    },
                    "B.E. Electrical & Electronics Engineering": {
                        "duration": "4 years",
                        "seats": 60,
                        "eligibility": "10+2 with Mathematics, Physics, and Chemistry"
                    },
                    "B.E. Electronics & Communication Engineering": {
                        "duration": "4 years",
                        "seats": 120,
                        "eligibility": "10+2 with Mathematics, Physics, and Chemistry"
                    },
                    "B.E. Mechanical Engineering": {
                        "duration": "4 years",
                        "seats": 120,
                        "eligibility": "10+2 with Mathematics, Physics, and Chemistry"
                    }
                }
            },
            "departments": [
                "Artificial Intelligence & Data Science",
                "Civil Engineering",
                "Computer Science & Engineering",
                "Electrical & Electronics Engineering",
                "Electronics & Communication Engineering",
                "Mechanical Engineering",
                "Science & Humanities"
            ]
        },
        "admissions": {
            "process": [
                "TNEA Counselling (Tamil Nadu Engineering Admissions)",
                "Management Quota Admissions"
            ],
            "documents_required": [
                "10th Mark Sheet",
                "12th Mark Sheet",
                "Transfer Certificate",
                "Community Certificate",
                "Nativity Certificate",
                "Passport size photographs",
                "Aadhaar Card"
            ],
            "important_dates": {
                "application_start": "May",
                "application_end": "July",
                "academic_year_start": "August/September"
            }
        },
        "facilities": {
            "infrastructure": {
                "campus": {
                    "area": "20 acres",
                    "green_campus": True,
                    "wifi_enabled": True
                },
                "library": {
                    "books": "More than 20,000",
                    "e_resources": True,
                    "digital_library": True
                },
                "laboratories": {
                    "computer_labs": True,
                    "research_labs": True,
                    "engineering_labs": True
                },
                "sports": {
                    "indoor": [
                        "Table Tennis",
                        "Chess",
                        "Carrom",
                        "Gymnasium"
                    ],
                    "outdoor": [
                        "Cricket",
                        "Football",
                        "Basketball",
                        "Volleyball"
                    ]
                }
            },
            "amenities": {
                "hostel": {
                    "boys_hostel": True,
                    "girls_hostel": True,
                    "mess_facility": True
                },
                "transport": {
                    "college_bus": True,
                    "routes": "Covering major areas of Coimbatore"
                },
                "medical": {
                    "health_center": True,
                    "ambulance": True
                },
                "cafeteria": True,
                "atm": True,
                "temple": True
            }
        },
        "placements": {
            "highlights": {
                "placement_percentage": "Above 90%",
                "top_recruiters": [
                    "TCS",
                    "Infosys",
                    "Wipro",
                    "CTS",
                    "HCL",
                    "Amazon",
                    "Zoho"
                ],
                "highest_package": "Best in class compensation packages",
                "average_package": "Competitive industry standards"
            },
            "training": [
                "Soft Skills Development",
                "Technical Training",
                "Mock Interviews",
                "Group Discussions",
                "Personality Development"
            ]
        },
        "research": {
            "centers": [
                "Materials Processing And Testing Laboratory",
                "Renewable Energy & Computation Fluid Dynamics Lab",
                "Water And Sanitation Laboratory",
                "Polymer Engineering Laboratory",
                "Nanocrystal design and application Laboratory",
                "Functional Materials Laboratory",
                "Waste valorization Center"
            ],
            "publications": {
                "journals": True,
                "conferences": True,
                "patents": True
            },
            "collaborations": {
                "industry": True,
                "academic": True,
                "international": True
            }
        },
        "student_life": {
            "clubs": [
                "Technical Clubs",
                "Cultural Clubs",
                "Sports Clubs",
                "Social Service Clubs"
            ],
            "events": [
                "Technical Symposiums",
                "Cultural Festivals",
                "Sports Meets",
                "Workshops",
                "Guest Lectures"
            ],
            "activities": [
                "NSS",
                "NCC",
                "YRC",
                "Rotaract"
            ]
        },
        "achievements": {
            "rankings": [
                "NAAC A+ Grade",
                "NBA Accredited Programs",
                "Among Top Engineering Colleges in Tamil Nadu"
            ],
            "awards": [
                "Excellence in Academic Performance",
                "Research Contributions",
                "Industry Collaboration"
            ]
        }
    }

def process_urls(urls: List[str]) -> Dict[str, Any]:
    """Process a list of URLs and collect data"""
    college_data = generate_base_college_data()
    
    for url in urls:
        logger.info(f"Processing URL: {url}")
        data = scrape_url(url)
        if data:
            college_data = merge_data(college_data, {"pages": {url: data}})
    
    return college_data

def save_college_data(data: Dict[str, Any], filename: str = 'college_data.json'):
    """Save college data to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_urls_from_file(filename: str = 'urls.txt') -> List[str]:
    """Load URLs from a text file"""
    urls = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
    except Exception as e:
        logger.error(f"Error loading URLs from {filename}: {str(e)}")
    return urls

def check_for_new_cutoffs(base_url: str = "https://psgitech.ac.in/cutt-off") -> List[Dict[str, Any]]:
    """Check for new cut-off PDFs and return their data"""
    try:
        response = requests.get(base_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        new_cutoffs = []
        
        # Find all PDF links
        pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf') and 'cut_off' in x.lower())
        
        for link in pdf_links:
            pdf_url = link['href']
            if not pdf_url.startswith('http'):
                pdf_url = base_url + '/' + pdf_url
            
            # Check if this PDF is already processed
            if not is_pdf_processed(pdf_url):
                pdf_data = scrape_url(pdf_url)
                if pdf_data:
                    new_cutoffs.append(pdf_data)
                    mark_pdf_as_processed(pdf_url)
        
        return new_cutoffs
    except Exception as e:
        logger.error(f"Error checking for new cutoffs: {str(e)}")
        return []

def is_pdf_processed(pdf_url: str) -> bool:
    """Check if a PDF has already been processed"""
    try:
        with open('processed_pdfs.txt', 'r') as f:
            processed_urls = f.read().splitlines()
        return pdf_url in processed_urls
    except FileNotFoundError:
        return False

def mark_pdf_as_processed(pdf_url: str):
    """Mark a PDF as processed"""
    with open('processed_pdfs.txt', 'a') as f:
        f.write(f"{pdf_url}\n")

def update_cutoff_data():
    """Update cut-off data with any new PDFs"""
    new_cutoffs = check_for_new_cutoffs()
    if new_cutoffs:
        try:
            with open('college_data.json', 'r') as f:
                college_data = json.load(f)
        except FileNotFoundError:
            college_data = {"pages": {}}
        
        # Update with new cut-off data
        for cutoff in new_cutoffs:
            url = cutoff.get('url')
            if url:
                college_data['pages'][url] = cutoff
        
        # Save updated data
        with open('college_data.json', 'w') as f:
            json.dump(college_data, f, indent=2)
        
        logger.info(f"Updated cut-off data with {len(new_cutoffs)} new PDFs")
    return new_cutoffs

if __name__ == "__main__":
    # Load URLs from file
    urls = load_urls_from_file()
    
    # Process URLs and collect data
    college_data = process_urls(urls)
    
    # Check for new cut-offs
    new_cutoffs = update_cutoff_data()
    
    # Save the collected data
    save_college_data(college_data)
    logger.info("Data collection completed and saved to college_data.json") 