from django import forms

# Add any dashboard-related forms here if needed
# For example, if you have a dashboard settings form:

class DashboardSettingsForm(forms.Form):
    items_per_page = forms.IntegerField(min_value=5, max_value=100, initial=20)
    show_notifications = forms.BooleanField(required=False, initial=True)
    theme = forms.ChoiceField(choices=[('light', 'Light'), ('dark', 'Dark')], initial='light')