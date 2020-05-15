#====================================================================
# responses
from django.shortcuts import render
from django.http import HttpResponse

# db/model stuff
from pages.models import *
#====================================================================

def frontend(request):
  nets = Network.objects.all()
  rc = { 'networks': nets }

  return render(request, 'pages/frontend.html', { 'rc': rc } )