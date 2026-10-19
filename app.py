from flask import Flask, render_template, request
import sqlite3
from pathlib import Path
from math import isfinite

app = Flask(__name__)
DATABASE = Path(__file__).resolve().parent / 'motorbikes.db'


def create_connection(db_file):
    return sqlite3.connect(db_file)


def get_motorbikes(query, parameters=()):
    con = create_connection(DATABASE)
    try:
        cur = con.cursor()
        cur.execute(query, parameters)
        return cur.fetchall()
    finally:
        con.close()


BIKE_COLUMNS = 'ID, "Bike Model", Year, Manufacturer, CC, LAMS, "Production Country", "Cost (NZD)", Quickshifter, Type'


@app.route('/')
def render_index():
    return render_template('index.html')


@app.route('/motorbikes')
def render_motorbikes():
    fields = ['search', 'manufacturer', 'type', 'year', 'lams', 'quickshifter', 'min_price', 'max_price', 'min_cc', 'max_cc', 'sort']
    filters = {field: request.values.get(field, '').strip() for field in fields}
    conditions = []
    parameters = []
    errors = []

    if filters['search']:
        search = '%' + filters['search'] + '%'
        conditions.append('(\"Bike Model\" LIKE ? OR Manufacturer LIKE ? OR Type LIKE ? OR \"Production Country\" LIKE ? OR ID LIKE ? OR Year LIKE ? OR CC LIKE ?)')
        parameters.extend([search] * 7)

    for field, column in [('manufacturer', 'Manufacturer'), ('type', 'Type'), ('year', 'Year'), ('lams', 'LAMS'), ('quickshifter', 'Quickshifter')]:
        if filters[field]:
            conditions.append(column + ' = ?')
            parameters.append(filters[field])

    numbers = {}
    for field, column, comparison, label in [('min_price', '"Cost (NZD)"', '>=', 'Minimum price'), ('max_price', '"Cost (NZD)"', '<=', 'Maximum price'), ('min_cc', 'CC', '>=', 'Minimum CC'), ('max_cc', 'CC', '<=', 'Maximum CC')]:
        if filters[field]:
            try:
                value = float(filters[field])
                if not isfinite(value) or value < 0:
                    raise ValueError
                numbers[field] = value
                conditions.append(column + ' ' + comparison + ' ?')
                parameters.append(value)
            except ValueError:
                errors.append(label + ' must be a number of zero or more.')

    for minimum, maximum, label in [('min_price', 'max_price', 'price'), ('min_cc', 'max_cc', 'CC')]:
        if minimum in numbers and maximum in numbers and numbers[minimum] > numbers[maximum]:
            errors.append('Minimum ' + label + ' must not be greater than maximum ' + label + '.')

    sorts = {'model': '"Bike Model" COLLATE NOCASE, Manufacturer COLLATE NOCASE', 'price_low': '"Cost (NZD)" ASC', 'price_high': '"Cost (NZD)" DESC', 'cc_low': 'CC ASC', 'cc_high': 'CC DESC', 'year': 'Year DESC'}
    if filters['sort'] not in sorts:
        filters['sort'] = 'model'

    query = 'SELECT ' + BIKE_COLUMNS + ' FROM Motorcycle'
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    query += ' ORDER BY ' + sorts[filters['sort']] + ', ID'
    bike_list = [] if errors else get_motorbikes(query, parameters)

    manufacturers = get_motorbikes('SELECT DISTINCT Manufacturer FROM Motorcycle ORDER BY Manufacturer')
    types = get_motorbikes('SELECT DISTINCT Type FROM Motorcycle ORDER BY Type')
    years = get_motorbikes('SELECT DISTINCT Year FROM Motorcycle ORDER BY Year DESC')
    quickshifters = get_motorbikes('SELECT DISTINCT Quickshifter FROM Motorcycle ORDER BY Quickshifter')
    return render_template('motorbikes.html', bikes=bike_list, filters=filters, errors=errors, manufacturers=manufacturers, types=types, years=years, quickshifters=quickshifters), 400 if errors else 200


@app.route('/sport')
def render_sport():
    query = 'SELECT ' + BIKE_COLUMNS + ' FROM Motorcycle WHERE Type = ? ORDER BY "Bike Model" COLLATE NOCASE, Manufacturer COLLATE NOCASE, ID'
    bike_list = get_motorbikes(query, ('Sport',))
    return render_template('sport.html', bikes=bike_list)


@app.route('/naked')
def render_naked():
    query = 'SELECT ' + BIKE_COLUMNS + ' FROM Motorcycle WHERE Type = ? ORDER BY "Bike Model" COLLATE NOCASE, Manufacturer COLLATE NOCASE, ID'
    bike_list = get_motorbikes(query, ('Naked',))
    return render_template('naked.html', bikes=bike_list)


@app.route('/touring')
def render_touring():
    query = 'SELECT ' + BIKE_COLUMNS + ' FROM Motorcycle WHERE Type = ? ORDER BY "Bike Model" COLLATE NOCASE, Manufacturer COLLATE NOCASE, ID'
    bike_list = get_motorbikes(query, ('Touring',))
    return render_template('touring.html', bikes=bike_list)


@app.route('/lams')
def render_lams():
    search = request.args.get('search', '').strip()
    query = 'SELECT ' + BIKE_COLUMNS + ' FROM Motorcycle WHERE LAMS = ?'
    parameters = ['Yes']
    if search:
        query += ' AND ("Bike Model" LIKE ? OR Manufacturer LIKE ? OR Type LIKE ? OR "Production Country" LIKE ?)'
        parameters.extend(['%' + search + '%'] * 4)
    query += ' ORDER BY "Bike Model" COLLATE NOCASE, Manufacturer COLLATE NOCASE, ID'
    bike_list = get_motorbikes(query, parameters)
    return render_template('lams.html', bikes=bike_list, search=search)


@app.route('/search', methods=['GET', 'POST'])
def render_search():
    return render_motorbikes()


if __name__ == '__main__':
    app.run()
