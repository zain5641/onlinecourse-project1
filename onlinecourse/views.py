import logging
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.urls import reverse
from django.views import generic
from django.contrib.auth.decorators import login_required

from .models import Course, Enrollment, Question, Choice, Submission

logger = logging.getLogger(__name__)


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except User.DoesNotExist:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(
                username=username, first_name=first_name,
                last_name=last_name, password=password
            )
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_details_bootstrap.html'


def enroll(request, course_id):
    course = Course.objects.get(id=course_id)
    user = request.user

    is_enrolled = Enrollment.objects.filter(user=user, course=course).exists()
    if not is_enrolled and user.is_authenticated:
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# Task 5: submit function
@login_required
def submit(request, course_id):
    user = request.user
    course = Course.objects.get(id=course_id)
    enrollment = Enrollment.objects.get(user=user, course=course)

    submission = Submission.objects.create(enrollment=enrollment)

    selected_choices = extract_answers(request)
    submission.choices.set(selected_choices)
    submission.save()

    return HttpResponseRedirect(
        reverse(viewname='onlinecourse:show_exam_result', args=(course.id, submission.id))
    )


def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            submitted_answers.append(int(value))
    return submitted_answers


# Task 5: show_exam_result function
def show_exam_result(request, course_id, submission_id):
    course = Course.objects.get(id=course_id)
    submission = Submission.objects.get(id=submission_id)
    selected_choices = submission.choices.all()

    total_score = 0
    for question in course.questions.all():
        selected_ids = [choice.id for choice in selected_choices if choice.question_id == question.id]
        if question.is_get_score(selected_ids):
            total_score += question.grade

    context = {
        'course': course,
        'submission': submission,
        'selected_choices': selected_choices,
        'grade': total_score,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
