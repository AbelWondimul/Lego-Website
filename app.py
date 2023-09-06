from flask import Flask, request,render_template
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    "host=db dbname=postgres user=postgres password=postgres",
    cursor_factory=RealDictCursor)
app = Flask(__name__, template_folder= '')

SORT_COLUMNS ={"set_name", "year", "theme_name", "part_count"}
SORT_ORDER ={"asc","desc"}
LIMIT ={10,50,100}


def parse_int_list(value, valid_values, default_value):
    try:
        int_value = value
        for v in valid_values:
            if v == int_value:
                return v
        return default_value
    except:
        return default_value
def parse_int_list2(value, valid_values, default_value):
    try:
        int_value = int(value)
        for v in valid_values:
            if v == int_value:
                return v
        return default_value
    except:
        return default_value
def check_part(value, default_value):
    try:
        part_count_gte = int(value)
        if part_count_gte < 0:
            return default_value
        return part_count_gte
    except:
        return default_value
    

    
@app.route("/")
def hello_world():
    name = request.args.get("name", "World")
    return f"<p>Hello, {name}!</p>"

@app.route("/sets", methods= ['GET', 'POST'])
def render_sets():
    if request.method == 'POST':
        set_name = request.form["set_name"]
        theme_name = request.form["theme_name"]
        limit = request.form["limit"]
        part_count_gte = request.form["part_count_gte"]
        part_count_lte = request.form["part_count_lte"]
        sort_by = request.form["sort_by"]
        sort_dir = request.form["sort_dir"]
        page_num = request.form["page_num"]
        

    else:
        set_name = request.args.get("set_name", "")
        theme_name = request.args.get("theme_name", "")
        limit = parse_int_list2(request.args.get("limit", 50, type= int),{10,20,50}, 50)
        part_count_gte = check_part(request.args.get("part_count_gte", 0, type=int),0)
        part_count_lte = check_part(request.args.get("part_count_lte", 100000, type=int),100000)
        sort_by = parse_int_list(request.args.get("sort_by", "set_name"),{"set_name", "year", "theme_name", "part_count"},"set_name")
        sort_dir = parse_int_list(request.args.get("sort_dir","asc"),{"asc","desc"}, "asc")
        page_num = check_part(request.args.get("page_num",1, type=int),1)

   
    
    if sort_dir not in SORT_ORDER:
        sort_dir = "asc"
    if sort_by not in SORT_COLUMNS:
        sort_by = "set_name"
        
    from_where_clause =f"""
    from set s
    inner join theme t on s.theme_id = t.id
    inner join inventory i on s.set_num = i.set_num
    inner join inventory_part ip on ip.inventory_id = i.id 
    where s.name ilike %(set_name)s
        and t.name ilike %(theme_name)s
     group by s.name,s.year,t.name,s.set_num
     having Count(s.num_parts) >= %(part_count_gte)s and Count(s.num_parts) <= %(part_count_lte)s
     order by {sort_by} {sort_dir}
     limit %(limit)s
     offset %(offset)s
    """
    #

    params = {
        "set_name": f"%{set_name}%",
        "theme_name": f"%{theme_name}%",
        "limit": limit,
        "part_count_gte": part_count_gte,
        "part_count_lte": part_count_lte,
        "offset" : (page_num-1)*limit
    }
    def get_sort_dir(col):
        if col == sort_by:
            if sort_dir == "asc":
                return "desc"
            else:
                return "asc" 
        else:
            return "asc"
    def get_page_num(name):
        if name != 1:
            return page_num
        else:
            return 1

    with conn.cursor() as cur:
        cur.execute(f"""select s.name as set_name,Count(s.num_parts) as part_count, s.year,t.name as theme_name, s.set_num as set_num
                        {from_where_clause}""",
                    params)
        results = list(cur.fetchall())

        cur.execute("""select count(*) from 
                    (select s.name as set_name 
                    from set s 
    inner join theme t on s.theme_id = t.id
    inner join inventory i on s.set_num = i.set_num
    inner join inventory_part ip on ip.inventory_id = i.id 
    where s.name ilike %(set_name)s
        and t.name ilike %(theme_name)s
     group by s.name,s.year,t.name,s.set_num
     having Count(s.num_parts) >= %(part_count_gte)s and Count(s.num_parts) <= %(part_count_lte)s) as count""",
     params)
        count = cur.fetchone()["count"]

   

        return render_template("sets.html",
                               params=request.args,
                               result_count_r=count,
                               sets=results,
                               per_page = limit,
                               get_sort_dir=get_sort_dir,
                               get_page_num=get_page_num)
    