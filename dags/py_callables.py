import os
import pandas as pd
import datetime
import time
from airflow.exceptions import AirflowFailException
from airflow.providers.postgres.hooks.postgres import PostgresHook

exec_datetime = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
exec_date = datetime.datetime.now().strftime("%Y%m%d")
alcoholic_tbl_name = 'consumption_alcoholic_{pipeline_exc_date}'.format(pipeline_exc_date = exec_date)
cereals_bakery_tbl_name = 'consumption_cereals_bakery_{pipeline_exc_date}'.format(pipeline_exc_date = exec_date)
meats_poultry_tbl_name = 'consumption_meats_poultry_{pipeline_exc_date}'.format(pipeline_exc_date = exec_date)
alcoholic_file_name = '/opt/airflow/data/consumption_alcoholic_{exec_datetime}.csv'.format(exec_datetime = exec_date)
cereals_bakery_file_name = '/opt/airflow/data/consumption_cereals_bakery_{exec_datetime}.csv'.format(exec_datetime = exec_date)
meats_poultry_file_name = '/opt/airflow/data/consumption_meats_poultry_{exec_datetime}.csv'.format(exec_datetime = exec_date)
pg_hook = PostgresHook.get_hook('postgres')

def check_file_exists(ti):
    seconds_passed = 0
    file_exist = False

    while (seconds_passed < 900):
        if os.path.isfile('/opt/airflow/dags/consumption_yyyymmdd.csv'):
            file_exist = True
            break
        else:    
            print("File not found, try again in 5 minutes")
            time.sleep(300)
            seconds_passed += 300

    if file_exist == False:
        raise AirflowFailException("File not found")


def process_raw_data():
    df_raw = pd.read_csv('/opt/airflow/data/consumption_yyyymmdd.csv', header=0)
    df_needed = df_raw[df_raw.Category.isin(['Alcoholic beverages', 'Cereals and bakery products', 'Meats and poultry'])]
    df_needed.Month.astype(str)
    df_needed.Month = pd.to_datetime(df_needed['Month']).dt.strftime("%Y/%m/%d")
    df_needed['Pipeline_exc_datetime'] = exec_datetime

    df_needed.to_csv('/opt/airflow/data/staging_table.csv', index=False)


def insert_result():
    df_staging = pd.read_csv('/opt/airflow/data/staging_table.csv')
    df_alcoholic = df_staging[df_staging.Category == 'Alcoholic beverages']
    df_cereals_bakery = df_staging[df_staging.Category == 'Cereals and bakery products']
    df_meats_poultry = df_staging[df_staging.Category == 'Meats and poultry']

    df_alcoholic.to_csv(alcoholic_file_name, index=False)
    df_cereals_bakery.to_csv(cereals_bakery_file_name, index=False)
    df_meats_poultry.to_csv(meats_poultry_file_name, index=False)

    pg_hook.copy_expert("COPY {alcoholic_tbl_name} FROM stdin WITH CSV HEADER DELIMITER AS ',';"
                        .format(alcoholic_tbl_name = alcoholic_tbl_name)
                        ,alcoholic_file_name)
    pg_hook.copy_expert("COPY {cereals_bakery_tbl_name} FROM stdin WITH CSV HEADER DELIMITER AS ',';"
                        .format(cereals_bakery_tbl_name = cereals_bakery_tbl_name)
                        ,cereals_bakery_file_name)
    pg_hook.copy_expert("COPY {meats_poultry_tbl_name} FROM stdin WITH CSV HEADER DELIMITER AS ',';"
                        .format(meats_poultry_tbl_name = meats_poultry_tbl_name)
                        ,meats_poultry_file_name)

def validate_result():
    alcoholic_tbl_rows = pg_hook.get_first("SELECT COUNT(*) FROM " + alcoholic_tbl_name)[0]
    cereal_bakery_tbl_rows = pg_hook.get_first("SELECT COUNT(*) FROM " + cereals_bakery_tbl_name)[0]
    meat_poultry_tbl_rows = pg_hook.get_first("SELECT COUNT(*) FROM " + meats_poultry_tbl_name)[0]

    alcoholic_file_rows = len(pd.read_csv(alcoholic_file_name, index_col=0))
    cereal_bakery_file_rows = len(pd.read_csv(cereals_bakery_file_name, index_col=0))
    meat_poultry_file_rows = len(pd.read_csv(meats_poultry_file_name, index_col=0))

    if alcoholic_tbl_rows == alcoholic_file_rows and cereal_bakery_tbl_rows == cereal_bakery_file_rows and meat_poultry_tbl_rows == meat_poultry_file_rows:
        print("Import data successful")
    else:
        if alcoholic_tbl_rows != alcoholic_file_rows:
            raise AirflowFailException("Error: number of rows in alcoholic tables: {alcoholic_tbl_rows} don't match with file input: {alcoholic_file_rows}"
                                       .format(alcoholic_tbl_rows = alcoholic_tbl_rows, alcoholic_file_rows = alcoholic_file_rows))
        elif cereal_bakery_tbl_rows != cereal_bakery_file_rows:
            raise AirflowFailException("Error: number of rows in cereals and bakery table:{cereal_bakery_tbl_rows} don't match with file input : {cereal_bakery_file_rows}"
                                       .format(cereal_bakery_tbl_rows = cereal_bakery_tbl_rows, cereal_bakery_file_rows = cereal_bakery_file_rows))
        else:
            raise AirflowFailException("Error: number of rows in meat and poultry tables: {meat_poultry_tbl_rows} don't match with file input: {meat_poultry_file_rows}"
                                       .format(meat_poultry_tbl_rows = meat_poultry_tbl_rows, meat_poultry_file_rows = meat_poultry_file_rows))

def log_task_info(**kwargs):
    end_datetime = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    total_duration = datetime.datetime.strptime(end_datetime, "%Y/%m/%d %H:%M:%S") - datetime.datetime.strptime(exec_datetime, "%Y/%m/%d %H:%M:%S")
    max_task_duration = 0
    min_task_duration = 100
    max_task_id = ""
    min_task_id = ""
    ti = kwargs['ti']
    for instance in ti.get_dagrun().get_task_instances():
        if instance.duration is not None:
            if instance.duration > max_task_duration:
                max_task_duration = instance.duration
                max_task_id = instance.task_id
            if instance.duration < min_task_duration:
                min_task_duration = instance.duration
                min_task_id = instance.task_id

    print("Task start time: {exec_datetime}".format(exec_datetime = exec_datetime))
    print("Task end time: {end_date}".format(end_date = end_datetime))
    print("Total duration: {total_duration}".format(total_duration = total_duration))
    print("Task with longest duration: {max_task_id} - {max_task_duration} seconds".format(max_task_id = max_task_id, max_task_duration = max_task_duration))
    print("Task with shortest duration: {min_task_id} - {min_task_duration} seconds".format(min_task_id = min_task_id, min_task_duration = min_task_duration))      