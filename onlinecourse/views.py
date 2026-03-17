from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission  # Añadidos Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Create your views here.

def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
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


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment
def submit(request, course_id):
    """Submit exam answers and create submission record"""
    # Get user and course object
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    
    # Get the associated enrollment object created when the user enrolled the course
    enrollment = Enrollment.objects.get(user=user, course=course)
    
    # Create a submission object referring to the enrollment
    submission = Submission.objects.create(enrollment=enrollment)
    
    # Collect the selected choices from exam form
    selected_choice_ids = extract_answers(request)
    
    # Get the actual Choice objects and add to submission
    choices = Choice.objects.filter(id__in=selected_choice_ids)
    submission.choices.set(choices)
    
    # Redirect to show_exam_result with the submission id
    return HttpResponseRedirect(
        reverse('onlinecourse:exam_result', 
                args=(course.id, submission.id))
    )


# An example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
    """Extract selected choice IDs from POST data"""
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_answers.append(choice_id)
    return submitted_answers


# <HINT> Create an exam result view to check if learner passed exam and show their question results
def show_exam_result(request, course_id, submission_id):
    """Show exam results with score and question-by-question feedback"""
    # Get course and submission based on their ids
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)
    
    # Get the selected choice ids from the submission record
    selected_choices = submission.choices.all()
    
    # Calculate the total score
    total_score = 0
    questions = course.question_set.all()
    
    # For each question, check if selected choices match correct choices
    for question in questions:
        # Get all correct choices for this question
        correct_choices = question.choice_set.filter(is_correct=True)
        # Get user's selected choices for this question
        selected_for_question = selected_choices.filter(question=question)
        
        # Check if the selected choices are exactly the correct ones
        if set(correct_choices) == set(selected_for_question):
            total_score += question.grade
    
    # Prepare context for template
    context = {
        'course': course,
        'grade': total_score,
        'submission': submission,
        'selected_choices': selected_choices,
        'questions': questions,
    }
    
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)