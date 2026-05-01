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






# forms.py

class ZapasForm(forms.ModelForm):
    class Meta:
        model = Zapas
        fields = ['datum', 'hrac_domaci', 'hrac_hoste', 'set1', 'set2', 'set3', 'mice_bere_domaci']
        widgets = {
            'datum': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # 1. Vytáhneme si uživatele z parametrů (předáme ho z view)
        user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)

        # Vaše stávající úprava pro set3
        self.fields['set3'] = forms.CharField(
            widget=forms.TextInput(attrs={
                'placeholder': 'např. 10:8',
                'style': 'width: 100px; text-align: center;',
                'class': 'form-control'
            }),
            initial='0:0',
            required=False
        )

        # 2. LOGIKA OPRÁVNĚNÍ:
        # Pokud uživatel není superuser, pole zakážeme (bude jen pro čtení) nebo schováme
        if user and not user.is_superuser:
            # Možnost A: Pole je vidět, ale nejde změnit (disabled)
            self.fields['mice_bere_domaci'].disabled = True
            self.fields['mice_bere_domaci'].help_text = "Pouze správce může měnit držitele míčů."
            
            # Možnost B: Pole úplně schovat
            # self.fields['mice_bere_domaci'].widget = forms.HiddenInput()