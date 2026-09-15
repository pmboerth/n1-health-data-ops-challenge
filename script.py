import sqlite3

# Open a connection to the database
connection = sqlite3.connect("n1_data_ops_challenge.db")
cursor = connection.cursor()

# Create standard member table
try:
    cursor.execute("DROP TABLE IF EXISTS std_member_info;")
    
    cursor.execute("""
        CREATE TABLE std_member_info (
            member_id TEXT PRIMARY KEY,
            member_first_name TEXT,
            member_last_name TEXT,
            date_of_birth TEXT,
            main_address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            payer TEXT,
            eligibility_start_date TEXT,
            eligibility_end_date TEXT
        );
    """)
    connection.commit()

except sqlite3.Error as e:
    connection.rollback()
    connection.close()
    print(f"Error during table creation: {e}")
    raise

# Insert data into standard member table
# DISTINCT use okay here, confirmed duplicates across rosters were exact
try:
    cursor.execute("""
        INSERT INTO std_member_info
        SELECT DISTINCT Person_Id, First_Name, Last_Name, Dob,
                        Street_Address, City, State, Zip, payer,
                        eligibility_start_date, eligibility_end_date
        FROM (
            -- roster_1: already standard
            SELECT Person_Id, First_Name, Last_Name, Dob,
                   Street_Address, City, State, Zip, payer,
                   eligibility_start_date, eligibility_end_date
            FROM roster_1
            
            UNION ALL
            
            -- roster_2: dates need MM/DD/YYYY -> YYYY-MM-DD conversion
            SELECT Person_Id, First_Name, Last_Name,
                   substr(Dob, 7, 4) || '-' || substr(Dob, 1, 2) || '-' || substr(Dob, 4, 2),
                   Street_Address, City, State, Zip, payer,
                   substr(eligibility_start_date, 7, 4) || '-' || substr(eligibility_start_date, 1, 2) || '-' || substr(eligibility_start_date, 4, 2),
                   substr(eligibility_end_date, 7, 4) || '-' || substr(eligibility_end_date, 1, 2) || '-' || substr(eligibility_end_date, 4, 2)
            FROM roster_2
            
            UNION ALL
            
            -- roster_3: already standard
            SELECT Person_Id, First_Name, Last_Name, Dob,
                   Street_Address, City, State, Zip, payer,
                   eligibility_start_date, eligibility_end_date
            FROM roster_3
            
            UNION ALL
            
            -- roster_4: State needs CA -> California conversion
            SELECT Person_Id, First_Name, Last_Name, Dob, Street_Address, City,
                   CASE WHEN State = 'CA' THEN 'California' ELSE State END,
                   Zip, payer, eligibility_start_date, eligibility_end_date
            FROM roster_4
            
            UNION ALL
            
            -- roster_5: already standard, just has different column order
            SELECT Person_Id, First_Name, Last_Name, Dob,
                   Street_Address, City, State, Zip, payer,
                   eligibility_start_date, eligibility_end_date
            FROM roster_5
        ) AS combined_rosters
        WHERE eligibility_start_date <= '2026-12-31'
          AND eligibility_end_date >= '2026-01-01';              
    """)
    connection.commit()

except sqlite3.Error as e:
    connection.rollback()
    connection.close()
    print(f"Error during data insertion: {e}")
    raise

# Query 1: How many distinct members were eligible in April 2025
try:
    cursor.execute("""
        SELECT COUNT(DISTINCT member_id) AS member_count
        FROM std_member_info
        WHERE eligibility_start_date <= '2025-04-30'
          AND eligibility_end_date >= '2025-04-01';   
    """)
    
    result = cursor.fetchone()[0]
    print(f"Members eligible in April 2025: {result}")
    
except sqlite3.Error as e:
    print(f"ERROR executing Query: How many distinct members were eligible in April 2025. {e}")

# Query 2: How many members were included more than once?
try:
    cursor.execute("""
        SELECT COUNT(*) AS duplicate_members
        FROM (
            SELECT Person_Id
            FROM (
                SELECT Person_Id FROM roster_1
                UNION ALL
                SELECT Person_Id FROM roster_2
                UNION ALL
                SELECT Person_Id FROM roster_3
                UNION ALL
                SELECT Person_Id FROM roster_4
                UNION ALL
                SELECT Person_Id FROM roster_5
            )
            GROUP BY Person_Id
            HAVING COUNT(Person_Id) > 1
        );
    """)
    
    result = cursor.fetchone()[0]
    print(f"Members who were included more than once: {result}")
    
except sqlite3.Error as e:
    print(f"ERROR executing Query: How many members were included more than once. {e}")

# Query 3: What is the breakdown of members by payer?
try:
    cursor.execute("""
        SELECT payer, COUNT(member_id) AS member_count
        FROM std_member_info
        GROUP BY payer;
    """)
    
    results = cursor.fetchall()
    for payer, count in results:
        print(f"Members with payer '{payer}': {count}")
    
except sqlite3.Error as e:
    print(f"ERROR executing Query: What is the breakdown of members by payer. {e}")

# Query 4: How many members live in a zip code with a “Food access score” less than 2?
try:
    cursor.execute("""
        SELECT COUNT(DISTINCT members.member_id) AS member_count
        FROM std_member_info members
        JOIN model_scores_by_zip scores 
            ON members.zip_code = CAST(scores.zcta AS TEXT)
        WHERE scores.food_access_score < 2;
    """)
    
    result = cursor.fetchone()[0]
    print(f"Members who live in a zip code with a food access score less than 2: {result}")
    
except sqlite3.Error as e:
    print(f"ERROR executing Query: How many members live in a zip code with a 'Food access score' less than 2. {e}")

# Query 5: What is the average “Social isolation score” for all members?
try:
    cursor.execute("""
        SELECT AVG(scores.social_isolation_score) AS average_social_isolation_score
        FROM std_member_info members
        JOIN model_scores_by_zip scores
            ON members.zip_code = CAST(scores.zcta AS TEXT);
    """)
    
    result = cursor.fetchone()[0]
    print(f"Average social isolation score for all members: {result:.2f}")
  
except sqlite3.Error as e:
    print(f"ERROR executing Query: What is the average 'Social isolation score' for all members. {e}")

# Query 6: Which members live in the zip code with the highest “Algorex SDOH composite score”?
try:
    cursor.execute("""
        SELECT member_id, member_first_name, member_last_name, zip_code
        FROM std_member_info
        WHERE zip_code IN (
            SELECT CAST(zcta AS TEXT)
            FROM model_scores_by_zip
            WHERE algorex_sdoh_composite_score = (
                SELECT MAX(algorex_sdoh_composite_score) FROM model_scores_by_zip
            )
        );
    """)
    
    results = cursor.fetchall()
    print(f"Members in the zip code with the highest Algorex SDOH composite score:")
    for member_id, first_name, last_name, zip_code in results:
        print(f"  {member_id} - {first_name} {last_name} (zip: {zip_code})")

except sqlite3.Error as e:
    print(f"ERROR executing Query: Which members live in the zip code with the highest 'Algorex SDOH composite score'. {e}")
    
connection.close()