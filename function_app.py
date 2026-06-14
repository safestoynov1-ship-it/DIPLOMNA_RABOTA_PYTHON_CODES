import azure.functions as func
import logging
import pandas as pd
import io
import os
import pymssql
from azure.storage.blob import BlobServiceClient


app = func.FunctionApp()


# Извличане на параметрите от SQL connection string
def parse_sql_connection_string(conn_str):
    parts = {}

    for item in conn_str.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            parts[key.strip()] = value.strip()

    server = parts.get("Server", "").replace("tcp:", "").split(",")[0]
    database = parts.get("Initial Catalog") or parts.get("Database")
    user = parts.get("User ID")
    password = parts.get("Password")

    return server, database, user, password


# Почистване на текстови стойности
def clean_text(value, default="Unknown"):
    if pd.isna(value) or str(value).strip() == "" or str(value).strip().lower() == "none":
        return default
    return str(value).strip()


# Почистване на числови стойности
def clean_number(value, default=0):
    if pd.isna(value):
        return default
    try:
        return float(value)
    except:
        return default


# Почистване на целочислени стойности
def clean_int(value, default=0):
    if pd.isna(value):
        return default
    try:
        return int(value)
    except:
        return default


# HTTP-triggered функция за изпълнение на ETL процеса
@app.route(route="run-etl", auth_level=func.AuthLevel.FUNCTION)
def ETL_Process(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("HTTP ETL процесът е стартиран.")

    conn = None
    cursor = None

    try:
        file_name = req.params.get("file", "proba.csv")

        storage_conn_str = os.getenv("AzureWebJobsStorage")
        if not storage_conn_str:
            raise Exception("Липсва AzureWebJobsStorage.")

        blob_service_client = BlobServiceClient.from_connection_string(storage_conn_str)
        blob_client = blob_service_client.get_blob_client(
            container="shipping-data",
            blob=file_name
        )

        blob_data = blob_client.download_blob().readall()
        df = pd.read_csv(io.BytesIO(blob_data))

        logging.info(f"CSV файлът е прочетен успешно: {file_name}")
        logging.info(f"Редове: {len(df)}")
        logging.info(f"Колони: {list(df.columns)}")

        sql_conn_str = os.getenv("SqlConnectionString")
        if not sql_conn_str:
            raise Exception("Липсва SqlConnectionString.")

        server, database, user, password = parse_sql_connection_string(sql_conn_str)

        conn = pymssql.connect(
            server=server,
            user=user,
            password=password,
            database=database
        )

        cursor = conn.cursor()

        inserted_ships = 0
        inserted_routes = 0
        inserted_voyages = 0
        inserted_metrics = 0

        # Обхождане на редовете от CSV файла
        for _, row in df.iterrows():
            ship_type = clean_text(row["Ship_Type"])
            engine_type = clean_text(row["Engine_Type"])
            draft_meters = clean_number(row["Draft_meters"])

            route_type = clean_text(row["Route_Type"])
            weather_condition = clean_text(row["Weather_Condition"])
            distance_traveled = clean_number(row["Distance_Traveled_nm"])

            maintenance_status = clean_text(row["Maintenance_Status"])
            date_value = clean_text(row["Date"], "1900-01-01")

            cargo_weight = clean_number(row["Cargo_Weight_tons"])
            weekly_voyage_count = clean_int(row["Weekly_Voyage_Count"])
            turnaround_time = clean_number(row["Turnaround_Time_hours"])

            speed = clean_number(row["Speed_Over_Ground_knots"])
            engine_power = clean_number(row["Engine_Power_kW"])
            efficiency = clean_number(row["Efficiency_nm_per_kWh"])
            average_load = clean_number(row["Average_Load_Percentage"])
            operational_cost = clean_number(row["Operational_Cost_USD"])
            revenue = clean_number(row["Revenue_per_Voyage_USD"])
            seasonal_score = clean_number(row["Seasonal_Impact_Score"])

            # INSERT Ships
            cursor.execute('''
                INSERT INTO Ships (Ship_Type, Engine_Type, Draft_meters)
                VALUES (%s, %s, %s)
            ''', (
                ship_type,
                engine_type,
                draft_meters
            ))

            cursor.execute("SELECT SCOPE_IDENTITY()")
            ship_id = int(cursor.fetchone()[0])
            inserted_ships += 1

            # INSERT Routes
            cursor.execute('''
                INSERT INTO Routes (Route_Type, Weather_Condition, Distance_Traveled_nm)
                VALUES (%s, %s, %s)
            ''', (
                route_type,
                weather_condition,
                distance_traveled
            ))

            cursor.execute("SELECT SCOPE_IDENTITY()")
            route_id = int(cursor.fetchone()[0])
            inserted_routes += 1

            # INSERT Voyages
            cursor.execute('''
                INSERT INTO Voyages (
                    ShipID,
                    RouteID,
                    Date,
                    Cargo_Weight_tons,
                    Weekly_Voyage_Count,
                    Turnaround_Time_hours,
                    Maintenance_Status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                ship_id,
                route_id,
                date_value,
                cargo_weight,
                weekly_voyage_count,
                turnaround_time,
                maintenance_status
            ))

            cursor.execute("SELECT SCOPE_IDENTITY()")
            voyage_id = int(cursor.fetchone()[0])
            inserted_voyages += 1

            # INSERT PerformanceMetrics
            cursor.execute('''
                INSERT INTO PerformanceMetrics (
                    VoyageID,
                    Speed_Over_Ground_knots,
                    Engine_Power_kW,
                    Efficiency_nm_per_kWh,
                    Average_Load_Percentage,
                    Operational_Cost_USD,
                    Revenue_per_Voyage_USD,
                    Seasonal_Impact_Score
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                voyage_id,
                speed,
                engine_power,
                efficiency,
                average_load,
                operational_cost,
                revenue,
                seasonal_score
            ))

            inserted_metrics += 1

        conn.commit()

        message = (
            f"ETL процесът завърши успешно. "
            f"Ships: {inserted_ships}, "
            f"Routes: {inserted_routes}, "
            f"Voyages: {inserted_voyages}, "
            f"PerformanceMetrics: {inserted_metrics}"
        )

        logging.info(message)

        return func.HttpResponse(message, status_code=200)

    except Exception as e:
        logging.error(f"Грешка при ETL процеса: {str(e)}")

        if conn:
            conn.rollback()

        return func.HttpResponse(
            f"Грешка при ETL процеса: {str(e)}",
            status_code=500
        )

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
