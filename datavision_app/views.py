import uuid
from pathlib import Path
from django.shortcuts import render, redirect
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.utils.text import slugify
import pandas as pd
import numpy as np
import matplotlib

# Force a non-interactive backend so Matplotlib/Seaborn do not try to
# open a GUI when running inside the Django dev server thread.
try:
    matplotlib.use('Agg')
except Exception:
    pass
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.io as pio
from django.utils.safestring import mark_safe
from django.http import Http404


@require_http_methods(["GET", "POST"])
def home(request):
    """
    Home page: shows form to paste text or upload .txt file.
    On POST save the text to a file and redirect to a result page that renders a
    client-side wordcloud using a JS library (avoids server-side C-extension deps).
    """
    # For home, show the full data analysis UI (same as /analyze)
    return analyze(request)


def result(request, filename):
    # Read the saved text file and pass raw text to the template. The template will
    # render a client-side wordcloud using wordcloud2.js so Python doesn't need
    # the native `wordcloud` package.
    text_path = Path(settings.MEDIA_ROOT) / "wordcloud_texts" / filename
    if not text_path.exists():
        return render(request, "datavision_app/result.html", {"error": "Generated text not found.", "title": "Wordcloud — DataVision Pro"})
    raw_text = text_path.read_text(encoding="utf-8")
    return render(request, "datavision_app/result.html", {"raw_text": raw_text, "title": "Wordcloud — DataVision Pro"})


def analyze(request):
    """
    Analyze page: accept sample dataset choice or file upload, then show
    preview, missing values, summary statistics, pairplot (image), correlation
    heatmap (plotly), and an interactive plotly plot for selected numeric columns.
    """
    context = {}
    sample_choices = ["iris", "titanic", "tips", "diamonds"]
    context["sample_choices"] = sample_choices
    # auto-generated features for the Feature section
    context['features'] = [
        {"title": "Fast Exploratory Analysis", "desc": "Quickly preview datasets, missing values, and summary statistics."},
        {"title": "Interactive Plots", "desc": "Render scatter, line, bar, histogram and KDE plots with Plotly."},
        {"title": "Client-side Wordclouds", "desc": "Generate responsive wordclouds in the browser without native builds."},
        {"title": "Exportable Visuals", "desc": "Save pairplots and charts to share in reports."},
        {"title": "SEO-friendly Pages", "desc": "Static pages and semantic markup for better discoverability."},
    ]

    if request.method == "POST":
        selected = request.POST.get("sample_dataset")
        uploaded = request.FILES.get("datafile")
        # load dataframe
        try:
            if uploaded:
                if uploaded.name.endswith('.csv'):
                    try:
                        df = pd.read_csv(uploaded, encoding='utf-8')
                    except Exception:
                        df = pd.read_csv(uploaded, encoding='latin1')
                elif uploaded.name.endswith('.xlsx'):
                    df = pd.read_excel(uploaded)
                else:
                    df = pd.DataFrame()
                context['message'] = 'Custom dataset uploaded successfully.'
            else:
                df = sns.load_dataset(selected)
                context['message'] = f"Loaded sample dataset '{selected}'"
        except Exception as e:
            df = pd.DataFrame()
            context['error'] = f"Error loading dataset: {e}"

        if df.empty:
            context['error'] = context.get('error', 'No data available')
            return render(request, 'datavision_app/analyze.html', context)

        # Basic info
        context['df_head'] = df.head().to_html(classes='table', index=False, escape=False)
        context['n_rows'] = df.shape[0]
        context['n_cols'] = df.shape[1]
        context['dtypes'] = df.dtypes.to_frame('dtype').to_html(classes='table', escape=False)

        # Missing values
        missing = df.replace('', np.nan).isnull().sum()
        if missing.sum() > 0:
            context['missing_html'] = missing[missing > 0].sort_values(ascending=False).to_frame('missing').to_html(classes='table', escape=False)
        else:
            context['missing_html'] = None

        # Summary stats
        numeric_df = df.select_dtypes(include=[np.number])
        if not numeric_df.empty:
            context['summary_html'] = numeric_df.describe().to_html(classes='table', escape=False)
        else:
            context['summary_html'] = None

        # Ensure output dir
        outdir = Path(settings.MEDIA_ROOT) / 'analysis'
        outdir.mkdir(parents=True, exist_ok=True)

        # Pairplot (save as PNG) - use a subset if too many columns
        try:
            pairplot_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(pairplot_cols) >= 2:
                pp = sns.pairplot(df[pairplot_cols].dropna().iloc[:, :6])
                pp_fname = slugify(str(uuid.uuid4())) + '_pairplot.png'
                pp_path = outdir / pp_fname
                pp.fig.tight_layout()
                pp.fig.savefig(pp_path, dpi=150)
                plt.close(pp.fig)
                context['pairplot_url'] = settings.MEDIA_URL + 'analysis/' + pp_fname
            else:
                context['pairplot_url'] = None
        except Exception as e:
            context['pairplot_error'] = str(e)

        # Correlation heatmap (plotly)
        if not numeric_df.empty:
            corr = numeric_df.corr()
            heatmap_fig = go.Figure(data=go.Heatmap(z=corr.values, x=corr.columns, y=corr.columns, colorscale='Viridis'))
            heatmap_fig.update_layout(width=700, height=600, margin=dict(l=40, r=40, t=40, b=40))
            heatmap_html = pio.to_html(heatmap_fig, full_html=False, include_plotlyjs='cdn')
            context['heatmap_html'] = mark_safe(heatmap_html)
        else:
            context['heatmap_html'] = None

        # Interactive plot (plotly) for user-chosen x/y & type
        # take defaults: first two numeric columns
        if not numeric_df.empty and numeric_df.shape[1] >= 1:
            num_cols = numeric_df.columns.tolist()
            x_col = request.POST.get('x_col') or num_cols[0]
            y_col = request.POST.get('y_col') or (num_cols[1] if len(num_cols) > 1 else num_cols[0])
            plot_type = request.POST.get('plot_type') or 'Scatter'
            try:
                if plot_type == 'Line':
                    fig = go.Figure(data=go.Scatter(x=df[x_col], y=df[y_col], mode='lines+markers'))
                elif plot_type == 'Bar':
                    fig = go.Figure(data=go.Bar(x=df[x_col], y=df[y_col]))
                elif plot_type == 'Histogram':
                    fig = go.Figure(data=go.Histogram(x=df[x_col].dropna()))
                elif plot_type == 'KDE':
                    # approximate using histogram with density
                    fig = go.Figure(data=go.Histogram(x=df[x_col].dropna(), histnorm='probability density'))
                else:
                    fig = go.Figure(data=go.Scatter(x=df[x_col], y=df[y_col], mode='markers'))
                fig.update_layout(width=800, height=450, title=f"{plot_type} of {x_col} vs {y_col}")
                context['interactive_plot_html'] = mark_safe(pio.to_html(fig, full_html=False, include_plotlyjs=False))
            except Exception as e:
                context['interactive_error'] = str(e)
        else:
            context['interactive_plot_html'] = None

        # send list of numeric columns for form
        context['numeric_columns'] = numeric_df.columns.tolist()

        return render(request, 'datavision_app/analyze.html', context)

    # GET
    return render(request, 'datavision_app/analyze.html', context)


def blog(request):
    """Simple blog listing page using in-code `POSTS` storage."""
    posts = []
    for slug, p in POSTS.items():
        posts.append({"title": p['title'], "excerpt": p['excerpt'], "slug": slug})
    return render(request, 'datavision_app/blog.html', {"posts": posts, "title": "Blog — DataVision Pro"})


# In-code blog posts store
POSTS = {
    "introducing-datavision-pro": {
        "title": "Introducing DataVision Pro",
        "excerpt": "Powerful, professional data visualization and wordcloud tools.",
        "content": (
            "<p>DataVision Pro brings professional-grade data visualization and text analysis to your fingertips. "
            "Create beautiful, publication-ready charts, generate wordclouds from text data, and export results for reports.</p>"
            "<h3>Key capabilities</h3>"
            "<ul>"
            "<li>Fast, server-side data processing and client-side rendering for responsive UX.</li>"
            "<li>Multiple export options and shareable outputs.</li>"
            "<li>SEO- and accessibility-friendly pages for better discoverability.</li>"
            "</ul>"
        ),
    },
    "visualization-tips": {
        "title": "Tips for Better Visualizations",
        "excerpt": "Color, scale and layout tips for clearer charts.",
        "content": (
            "<p>Good visualizations communicate clearly. Here are practical tips:</p>"
            "<ol>"
            "<li><strong>Use color purposefully:</strong> Use a limited palette and reserve bright colors for emphasis.</li>"
            "<li><strong>Choose the right chart:</strong> Lines for trends, bars for comparisons, scatter for relationships.</li>"
            "<li><strong>Label clearly:</strong> Axis labels, units, and short titles help viewers understand quickly.</li>"
            "</ol>"
        ),
    },
}


def blog_post(request, slug):
    post = POSTS.get(slug)
    if not post:
        raise Http404("Post not found")
    return render(request, 'datavision_app/blog_post.html', {"post": post, "title": post['title']})


def contact(request):
    """Simple contact page placeholder."""
    message = None
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')
        outdir = Path(settings.MEDIA_ROOT) / 'contacts'
        outdir.mkdir(parents=True, exist_ok=True)
        fname = slugify(str(uuid.uuid4())) + '.txt'
        (outdir / fname).write_text(f"Name: {name}\nEmail: {email}\nMessage:\n{message_text}\n", encoding='utf-8')
        message = 'Thank you — your message was received.'
    return render(request, 'datavision_app/contact.html', {"message": message, "title": "Contact Us — DataVision Pro"})
