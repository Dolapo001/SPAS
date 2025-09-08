# # middleware.py
# from django.http import HttpResponseForbidden
# from django.contrib import messages
# from django.shortcuts import redirect
#
#
# class DepartmentAccessMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request):
#         response = self.get_response(request)
#         return response
#
#     def process_view(self, request, view_func, view_args, view_kwargs):
#         # Skip middleware for auth pages and admin
#         if not request.user.is_authenticated or request.user.is_superuser:
#             return None
#
#         # Check if user has a department
#         if not request.user.department:
#             messages.error(request, 'Your account is not associated with any department.')
#             return redirect('login')
#
#         # Add department to request for easy access in views
#         request.department = request.user.department
#
#         return None