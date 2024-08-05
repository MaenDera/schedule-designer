from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = '21b4d91f7466cee70c9f253b0724fdd9'

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/input', methods=['GET', 'POST'])
def input():
    if request.method == 'POST':
        schedule = {
            'name': request.form['schedule_name'],
            'working_days': request.form.getlist('working_days'),
            'hours_per_day': request.form['hours_per_day'],
            'starting_hour': request.form['starting_hour'],
            'breaks_per_day': int(request.form['breaks_per_day']),
            'break_duration': int(request.form['break_duration']),
            'task_names': request.form['task_names'],
            'end_date': request.form['end_date'],
        }
        schedule_data = generate_schedule(schedule)
        session['schedule_name'] = schedule['name']
        session['schedule_data'] = schedule_data  
        return redirect(url_for('result_page')) 
    return render_template('input.html')

'''The generate_schedule function effectively integrates genetic algorithm results with schedule creation, 
ensuring optimal break distribution and a balanced workload throughout the given period.'''

def create_individual(num_tasks, num_breaks):
    breaks = sorted(random.sample(range(1, num_tasks), num_breaks))
    return breaks

def fitness_function(individual, task_lengths, break_length):
    total_work_time = sum(task_lengths)
    num_intervals = len(individual) + 1
    interval_length = total_work_time / num_intervals
    break_positions = [0] + individual + [len(task_lengths)]
    
    intervals = []
    for i in range(len(break_positions) - 1):
        work_time = sum(task_lengths[break_positions[i]:break_positions[i + 1]])
        intervals.append(work_time)
    
    deviation = sum(abs(interval - interval_length) for interval in intervals)
    return 1 / (1 + deviation)

def mutate(individual, num_tasks):
    if len(individual) > 0:
        idx = random.randint(0, len(individual) - 1)
        new_break = random.randint(1, num_tasks - 1)
        individual[idx] = new_break
        individual = sorted(list(set(individual)))[:len(individual)]

def crossover(parent1, parent2, num_breaks):
    if len(parent1) > 1:
        point = random.randint(1, len(parent1) - 1)
        child = parent1[:point] + [x for x in parent2 if x not in parent1[:point]]
    else:
        child = parent1[:]
    child = sorted(list(set(child)))
    if len(child) > num_breaks:
        child = child[:num_breaks]
    elif len(child) < num_breaks:
        child += random.sample(range(1, max(parent1[-1], parent2[-1])), num_breaks - len(child))
        child = sorted(list(set(child)))
    return child

def genetic_algorithm(task_lengths, num_breaks, break_length, population_size=50, generations=100, mutation_rate=0.1):
    num_tasks = len(task_lengths)
    population = [create_individual(num_tasks, num_breaks) for _ in range(population_size)]
    
    for generation in range(generations):
        population.sort(key=lambda ind: -fitness_function(ind, task_lengths, break_length))
        new_population = population[:2] 
        
        while len(new_population) < population_size:
            parent1, parent2 = random.choices(population[:10], k=2) 
            child = crossover(parent1, parent2, num_breaks)
            if random.random() < mutation_rate:
                mutate(child, num_tasks)
            new_population.append(child)
        
        population = new_population
    
    best_individual = max(population, key=lambda ind: fitness_function(ind, task_lengths, break_length))
    return best_individual

def generate_schedule(schedule):
    days_of_week = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4,
        'Saturday': 5,
        'Sunday': 6
    }

    working_days_names = schedule['working_days']
    working_days = [days_of_week[day] for day in working_days_names]
    breaks_per_day = schedule['breaks_per_day']
    break_duration = schedule['break_duration']
    task_names = schedule['task_names'].split(',')
    task_durations = list(map(int, schedule['hours_per_day'].split(',')))
    end_date = datetime.strptime(schedule['end_date'], '%Y-%m-%d')

    starting_hour = datetime.strptime(schedule['starting_hour'], '%H:%M').time()

    events = []
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    task_index = 0

    def get_next_working_day(current_date, working_days):
        while current_date.weekday() not in working_days:
            current_date += timedelta(days=1)
        return current_date

    best_breaks = genetic_algorithm(task_durations, breaks_per_day, break_duration)
    
    while current_date <= end_date:
        current_date = get_next_working_day(current_date, working_days)
        work_start_time = datetime.combine(current_date, starting_hour)
        task_start_time = work_start_time

        break_index = 0
        break_positions = [0] + best_breaks + [len(task_durations)]
        
        for i in range(len(break_positions) - 1):
            for j in range(break_positions[i], break_positions[i + 1]):
                task_duration = task_durations[task_index % len(task_durations)]
                task_end_time = task_start_time + timedelta(minutes=task_duration)
                
                events.append({
                    'title': task_names[task_index % len(task_names)],
                    'start': task_start_time.isoformat(),
                    'end': task_end_time.isoformat(),
                    'className': 'task-event'
                })
                
                task_start_time = task_end_time
                task_index += 1
            
            if i < len(break_positions) - 2:
                break_start_time = task_start_time
                break_end_time = break_start_time + timedelta(minutes=break_duration)
                
                events.append({
                    'title': f'Break {break_index + 1}',
                    'start': break_start_time.isoformat(),
                    'end': break_end_time.isoformat(),
                    'className': 'break-event'
                })
                
                task_start_time = break_end_time
                break_index += 1

        current_date += timedelta(days=1)
        task_index = 0

    return {
        'events': events,
    }

@app.route('/result')
def result_page():
    schedule_name = session.get('schedule_name')
    schedule_data = session.get('schedule_data', {})
    return render_template('result.html', schedule_name=schedule_name, schedule=schedule_data)

if __name__ == '__main__':
    app.run(debug=True)
