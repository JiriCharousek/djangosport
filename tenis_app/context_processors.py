from tenis_app.models import Soutez

def souteze_context(request):
    """Zpřístupní proměnnou 'souteze' ve všech šablonách v projektu."""
    return {
        'souteze': Soutez.objects.all().order_by('nazev')
    }