from database.db_connection import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
SELECT 
    application_id,
    planning_office_comment,
    first_officer_comment,
    deputy_director_comment,
    committee_comment,
    admin_comment
FROM planning_applications
WHERE application_id = 1;
""")

row = cursor.fetchone()

if row:
    print("Application ID:", row["application_id"])
    print("Planning Office Comment:", row["planning_office_comment"])
    print("First Officer Comment:", row["first_officer_comment"])
    print("Deputy Director Comment:", row["deputy_director_comment"])
    print("Committee Comment:", row["committee_comment"])
    print("Admin Comment:", row["admin_comment"])
else:
    print("No application found with application_id = 1")

conn.close()