import frappe
from frappe.utils.nestedset import rebuild_tree

def execute():
	for doctype in ['department', 'leave_period', 'staffing_plan', 'job_opening']:
		frappe.reload_doc("hr", "doctype", doctype)

	companies = frappe.db.get_all("Company", fields=["name", "abbr"])
	departments = frappe.db.get_all("Department")
	comp_dict = {}

	# create a blank list for each company
	for company in companies:
		comp_dict[company.name] = {}

	for department in departments:
		# skip root node
		if department.name == "All Departments":
			continue

		# for each company, create a copy of the doc
		department_doc = frappe.get_doc("Department", department)
		for company in companies:
			copy_doc = frappe.copy_doc(department_doc)
			copy_doc.update({"company": company.name})
			copy_doc.insert()

			# append list of new department for each company
			comp_dict[company.name][department.name] = copy_doc.name

	rebuild_tree('Department', 'parent_department')
	doctypes = ["Asset", "Employee", "Leave Period", "Payroll Entry", "Staffing Plan", "Job Opening"]

	for d in doctypes:
		update_records(d, comp_dict)

	update_instructors(comp_dict)

def update_records(doctype, comp_dict):
	when_then = []
	for company in comp_dict:
		records = comp_dict[company]

		for department in records:
			when_then.append('''
				WHEN company = "%s" and department = "%s"
				THEN "%s"
			'''%(company, department, records[department]))

	frappe.db.sql("""
		update
			`tab%s`
		set
			department = CASE %s END
	"""%(doctype, " ".join(when_then)))

def update_instructors(comp_dict):
	when_then = []
	emp_details = frappe.get_all("Employee", fields=["name", "company"])

	for employee in emp_details:
		records = comp_dict[employee.company]

		for department in records:
			when_then.append('''
				WHEN employee = "%s" and department = "%s"
				THEN "%s"
			'''%(employee.name, department, records[department]))

	frappe.db.sql("""
		update
			`tabInstructor`
		set
			department = CASE %s END
	"""%(" ".join(when_then)))
