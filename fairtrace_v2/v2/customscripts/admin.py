# from my_app.forms import CustomForm
# class DuplicateChain(models.Model):
#     class Meta:
#         """Meta class for the above model."""
#         # abstract = True
# class MyCustomAdminForm(admin.ModelAdmin):
#     """
#     This is a funky way to register a regular view with the Django Admin.
#     """
#     def has_add_permission(*args, **kwargs):
#         return False
#     def has_change_permission(*args, **kwargs):
#         return True
#     def has_delete_permission(*args, **kwargs):
#         return False
#     def changelist_view(self, request):
#         context = {'title': 'My Custom AdminForm'}
#         if request.method == 'POST':
#             form = CustomForm(request.POST)
#             if form.is_valid():
#                 # Do your magic with the completed form data.
#                 # Let the user know that form was submitted.
#                 messages.success(request, 'Congrats, form submitted!')
#                 return HttpResponseRedirect('')
#             else:
#                 messages.error(
#                     request, 'Please correct the error below'
#                 )
#         else:
#             form = CustomForm()
#         context['form'] = form
#         return render(request, 'admin/change_form.html', context)
# from django import forms
# class CustomForm(forms.Form):
#     extra_field = forms.CharField()
# admin.site.register([DuplicateChain], MyCustomAdminForm)
# # from django import forms
# # class CustomForm(forms.Form):
# # Register your models here.
from django.contrib import admin

_admin_site_get_urls = admin.site.get_urls


def get_urls():
    """To perform function get_urls."""
    urls = _admin_site_get_urls()
    # urls += [
    #     url(
    #      r"^my_custom_view/$", admin.site.admin_view(MyCustomView.as_view())
    #     )
    # ]
    return urls


admin.site.get_urls = get_urls
