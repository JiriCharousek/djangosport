from django import forms
from .models import Zapas, Hrac

        

class HracForm(forms.ModelForm):
    class Meta:
        model = Hrac
        # Tímto řeknete Djangu, aby do formuláře zahrnulo všechna pole z modelu
        fields = '__all__' 
        
        # Přidání kalendáře pro datum a lepší stylování
        widgets = {
            'datum_narozeni': forms.DateInput(attrs={'type': 'date'}),
            'info': forms.Textarea(attrs={'rows': 4}),
        }








class ZapasForm(forms.ModelForm):
    class Meta:
        model = Zapas
        # Vynechali jsme sety_domaci a sety_hoste, protože se počítají samy
        fields = ['hrac_domaci', 'hrac_hoste', 'set1', 'set2', 'set3', 'odehrano', 'datum']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tímto změníme set3 z výběrového seznamu na volné textové pole
        self.fields['set3'] = forms.CharField(
            widget=forms.TextInput(attrs={
                'placeholder': 'např. 10:8',
                'style': 'width: 100px; text-align: center;',
                'class': 'form-control' # pokud používáš Bootstrap, jinak smaž
            }),
            initial='0:0',
            required=False
        )