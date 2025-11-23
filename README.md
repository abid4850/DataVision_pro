# DataVision Pro (datavision_pro)

Converted Streamlit wordcloud app into a Django website (datavision_pro) with professional UI/UX and server-side wordcloud generation.

Quick start (Windows PowerShell)

1. Open PowerShell in e:\Abid Hussain\wordcloud_app\datavision_pro

2. Create and activate virtual environment:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

3. Install dependencies:
   pip install -r requirements.txt

4. Apply migrations and prepare media folder:
   python manage.py migrate
   mkdir media
   mkdir media\wordclouds

5. Run development server:
   python manage.py runserver

6. Open in browser:
   http://127.0.0.1:8000/

Notes:
- Set DJANGO_SECRET_KEY and DJANGO_DEBUG environment variables for production.
- Static files are in datavision_app/static; generated images are saved to media/wordclouds.
