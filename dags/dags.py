from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from py_callables import check_file_exists, process_raw_data, insert_result, validate_result, log_task_info
from datetime import datetime

pipeline_exc_date = datetime.now().strftime("%Y%m%d")

alcoholic_tbl_name = 'consumption_alcoholic_{pipeline_exc_date}'.format(pipeline_exc_date = pipeline_exc_date)
cereals_bakery_tbl_name = 'consumption_cereals_bakery_{pipeline_exc_date}'.format(pipeline_exc_date = pipeline_exc_date)
meats_poultry_tbl_name = 'consumption_meats_poultry_{pipeline_exc_date}'.format(pipeline_exc_date = pipeline_exc_date)

sql_query = """CREATE TABLE IF NOT EXISTS {alcoholic_tbl_name}(
                category VARCHAR NOT NULL,
                sub_category  VARCHAR NOT NULL,
                aggregation_date  DATE NOT NULL,
                millions_of_dollar INT NOT NULL,
                pipeline_exc_datetime TIMESTAMP NOT NULL
            );
            CREATE TABLE IF NOT EXISTS {cereals_bakery_tbl_name}(
                category VARCHAR NOT NULL,
                sub_category  VARCHAR NOT NULL,
                aggregation_date  DATE NOT NULL,
                millions_of_dollar INT NOT NULL,
                pipeline_exc_datetime TIMESTAMP NOT NULL
            );
            CREATE TABLE IF NOT EXISTS {meats_poultry_tbl_name}(
                category VARCHAR NOT NULL,
                sub_category  VARCHAR NOT NULL,
                aggregation_date  DATE NOT NULL,
                millions_of_dollar INT NOT NULL,
                pipeline_exc_datetime TIMESTAMP NOT NULL
            );""" \
            .format(alcoholic_tbl_name = alcoholic_tbl_name, cereals_bakery_tbl_name = cereals_bakery_tbl_name, meats_poultry_tbl_name = meats_poultry_tbl_name)

with DAG("process_sale_data", schedule_interval=None,
    start_date=datetime(2023, 8, 29), catchup=False) as dag:

    check_file = PythonOperator(
        task_id='check_file_exist',
        python_callable= check_file_exists
    )

    process_data = PythonOperator(
        task_id='process_raw_data',
        python_callable=process_raw_data
    )

    create_result_table = PostgresOperator(
        task_id='create_result_table',
        postgres_conn_id="postgres",
        sql= sql_query
    )

    insert_result = PythonOperator(
        task_id='insert_result',
        python_callable=insert_result
    )

    validate_result = PythonOperator(
        task_id='validate_result',
        python_callable=validate_result
    )

    log_info = PythonOperator(
        task_id='log_info',
        python_callable=log_task_info
    )

check_file >> process_data >> create_result_table >> insert_result >> validate_result >> log_info