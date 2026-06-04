from django.shortcuts import get_object_or_404, render
from .models import DocumentPage


def document_view(request, slug):
    page = get_object_or_404(DocumentPage, slug=slug, is_published=True)
    return render(request, "documents/page.html", {"page": page})
