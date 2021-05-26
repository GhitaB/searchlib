# import json
from pprint import pprint
from xml.dom import minidom

import requests
from airflow.api.common.experimental.trigger_dag import trigger_dag
from airflow.decorators import dag, task
from airflow.exceptions import (AirflowException, DagNotFound,
                                DagRunAlreadyExists)
from airflow.models import (BaseOperator, BaseOperatorLink, DagBag, DagModel,
                            DagRun)
# from airflow.models import Variable
from airflow.operators import trigger_dagrun
from airflow.operators.python_operator import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.utils import timezone
from airflow.utils.dates import days_ago

import helpers
from bulk_trigger_dagrun import BulkTriggerDagRunOperator

# from airflow.operators import trigger_dagrun


# from ../scripts import crawler

# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    "owner": "airflow",
}


def get_sitemap(sitemap_url, ti):
    print("STEP 1")
    print(sitemap_url)
    res = requests.get(sitemap_url)
    print(res.content)
    print("STEP 2")
    # response = {'res':res.content}
    ti.xcom_push(key="response", value={"a": "b"})
    # return {'a':'b'}


@task()
def show_dag_run_conf(website_url, maintainer_email):
    # start_url, maintainer_email="no-reply@plone.org"
    print("website conf", website_url, maintainer_email)


@task()
def get_sitemap_url(website_url: str):
    sitemap_url = website_url.split("://")[-1] + "/sitemap.xml.gz"
    #        sitemap_url = (
    #            "gist.githubusercontent.com/zotya/cbc7af0b8d92e5547ae9"
    #            + "8db201f110b1/raw/f1227f8f903c4df3265c7498fd8a5408f9"
    #            + "c20334/gistfile1.txt"
    #        )
    print("sitemap_url", sitemap_url)
    return sitemap_url


@task()
def print_sitemap(sitemap: str):
    print("sitemap", sitemap)


@task()
def get_urls_from_sitemap(sitemap: str):
    response = []
    dom = minidom.parseString(sitemap)
    urls = dom.getElementsByTagName("url")
    for url in urls:
        item = {
            "url": url.getElementsByTagName("loc")[0].firstChild.nodeValue,
            "date": url.getElementsByTagName("lastmod")[0].firstChild.nodeValue,
        }
        response.append(item)
    print(response)
    return response


@task()
def print_urls(urls: object):
    print("urls:", urls)


@task(multiple_outputs=True)
def get_urls_to_update(urls: list = []) -> dict:
    my_clean_urls = []
    for url in urls:
        my_clean_urls.append(url["url"])
    print(my_clean_urls)
    return {"urls": my_clean_urls}


def trigger_fetch_for_urls(*args, **kwargs):
    # see https://stackoverflow.com/questions/41453379/execute-airflow-tasks-in-for-loop
    ti = kwargs["ti"]

    print("args")
    pprint(args)
    print("kwargs")
    pprint(kwargs)

    data = ti.xcom_pull(task_ids="get_urls_to_update")
    for x, url in enumerate(data["urls"]):
        print("Processing url", url)

        execution_date = timezone.utcnow()
        run_id = DagRun.generate_run_id(DagRunType.MANUAL, execution_date)
        try:
            # Ignore MyPy type for self.execution_date
            # because it doesn't pick up the timezone.parse() for strings
            dag_run = trigger_dag(
                dag_id="fetch_url",
                run_id=run_id,
                conf={"url": url, "maintainer_email": "tibi@example.com"},
                # execution_date=self.execution_date,
                replace_microseconds=False,
            )
            print(dag_run)
        except DagRunAlreadyExists as e:
            raise e

        # link = trigger_dagrun.TriggerDagRunOperator(
        #     task_id="trigger_fetch_url_%s" % x,
        #     trigger_dag_id="fetch_url",
        #     conf={"url": "url2", "maintainer_email": "tibi@example.com"},
        #     dag=kwargs["dag"],
        # )
        # print("link", link)

    # print(urls["urls"])
    # print(dir(trigger_dagrun))
    # link = trigger_dagrun.TriggerDagRunOperator(
    #     task_id="trigger_fetch_url1",
    #     trigger_dag_id="fetch_url",
    #     conf={"url": "url2", "maintainer_email": "tibi@example.com"},
    # )
    #
    # print("link", link)


@dag(
    default_args=default_args,
    schedule_interval=None,
    start_date=days_ago(2),
    tags=["crawl"],
)
def crawl_plonerestapi_website(website_url: str = "", maintainer_email: str = ""):
    """
    ### Crawls a plone.restapi powered website.

    Main task to crawl a website
    """

    show_dag_run_conf(website_url, maintainer_email)

    sitemap_url = get_sitemap_url(website_url)

    xc_sitemap = SimpleHttpOperator(
        task_id="get_sitemap",
        method="GET",
        endpoint=sitemap_url,
        #        http_conn_id="http_default",
        #        log_response=True,
    )

    print_sitemap(xc_sitemap.output)

    xc_urls = get_urls_from_sitemap(xc_sitemap.output)

    xc_clean_urls = get_urls_to_update(xc_urls)

    t3 = PythonOperator(
        task_id="trigger_fetch_for_urls",
        provide_context=True,
        python_callable=trigger_fetch_for_urls,
    )

    t3.set_upstream(xc_clean_urls)

    # trigger_fetch_for_urls(xc_clean_urls)
    # sitemap = PythonOperator(
    #    task_id = 'get_sitemap_request',
    #    python_callable = get_sitemap,
    #    op_kwargs={'sitemap_url':sitemap_url}
    # )

    # for x, url in enumerate(xc_clean_urls["urls"]):
    #     # print("trigger_url:", url)
    #     # task_id = "".join(e for e in url if e.isalnum())
    #     # print("task_id:", task_id)
    #     trigger_dagrun.TriggerDagRunOperator(
    #         task_id="trigger_dag_{}".format(x),
    #         trigger_dag_id="fetch_url",
    #         conf=url,
    #         # conf={"url": url, "maintainer_email": "tibi@example.com"},
    #     )

    # trigger_dagrun.TriggerDagRunOperator(
    #        task_id="trigger_fetch_url2",
    #        trigger_dag_id="fetch_url",
    #        conf={"url": "url3", "maintainer_email": "tibi@example.com"},
    #    )

    @task
    def get_urls_to_update(urls):
        my_clean_urls = []
        for url in urls:
            my_clean_urls.append(url["url"])
        print(my_clean_urls)
        return my_clean_urls

    clean_urls1 = get_urls_to_update(urls)

    @task
    def print_type(obj):
        print("type:", type(obj))
        print("len:", len(obj))
        print("first", obj[0])

    @task
    def trigger_fetch_for_urls(urls):
        print(urls)
        for url in urls:
            print(url)
            task_id = "fetch_url_" + helpers.nicename(url)
            BulkTriggerDagRunOperator(
                task_id=task_id,
                trigger_dag_id="fetch_url",
                conf={"url": url, "maintainer_email": "tibi@example.com"},
            )
            print("triggered")

    trigger_fetch_for_urls(clean_urls1)
    clean_urls2 = [
        "http://biodiversity.europa.eu/protected-areas/life-nature-and-biodiversity-projects"
    ]
    # , 'http://biodiversity.europa.eu/ecosystems/maes-viewer', 'http://biodiversity.europa.eu/fp-slide-3.jpg', 'http://biodiversity.europa.eu/biodiversity-data', 'http://biodiversity.europa.eu/biodiversity-data/overseas-country-and-territories', 'http://biodiversity.europa.eu/biodiversity-data/european-union', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/eu-wide-assessment-of-ecosystems-and-conditions']
    # , 'http://biodiversity.europa.eu/data/basic-countryfactsheet-statistics', 'http://biodiversity.europa.eu/image-3.jpg', 'http://biodiversity.europa.eu/image-6.jpg', 'http://biodiversity.europa.eu/image-7.jpg', 'http://biodiversity.europa.eu/protected-areas/size/clipboard-8939e268-223e-49bd-ad66-3fd92c366e36', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-d12bdec8-44a0-4ea0-8173-1541774f1c2c', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-9f47556f-21ac-4edc-a780-dec8ac3d6806', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-d23d3461-52a6-4a59-bbd9-18ab0cbcf025', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-6e2d9e73-2a6e-4eb9-a15f-973976b5c022', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/forest_-erno-endre-gergely.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/clipboard-232a0d77-39d7-42e2-bc7f-2e1fd532a7b8', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/fisheries_zvonimir-tanocki.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/sea_valeria-schettino.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/urban_joseph-galea.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/urban_joseph-galea-1.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/leisure_peter-vadocz.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/energy_eea.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/adaptation_antonio-farto.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/finance_william-richardson.jpg', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-88e6da1f-a464-41d4-a264-4d2a8b371240', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-concepts/clipboard-595b8386-b29a-4b62-b03b-dfb7f612ab3b', 'http://biodiversity.europa.eu/green-infrastructure/cost-and-benefits/clipboard-e785b66f-3b7a-4b5e-ac9e-f04dd4f4e9ad', 'http://biodiversity.europa.eu/green-infrastructure/cost-and-benefits/clipboard-72fb2cf4-6c4e-45bd-b2d0-edf907030ea4', 'http://biodiversity.europa.eu/protected-areas/future/natura_viktors-ozolins.png', 'http://biodiversity.europa.eu/case-study-hub/CS%20grasslands%20Poland', 'http://biodiversity.europa.eu/case-study-hub/cs-coastal-meadows-finland', 'http://biodiversity.europa.eu/case-study-hub/CS%20Dianthus%20diutinus%20Hungary', 'http://biodiversity.europa.eu/case-study-hub/CS%20humid%20dune%20slacks%20Netherlands', 'http://biodiversity.europa.eu/case-study-hub/mediterranean-killifish-aphanius-fasciatus', 'http://biodiversity.europa.eu/case-study-hub/CS%20Pond%20turtle%20Lithuania', 'http://biodiversity.europa.eu/case-study-hub/CS%20Taxus%20baccata%20British%20Isles', 'http://biodiversity.europa.eu/case-study-hub/CS%20Violet%20Copper%20Luxembourg', 'http://biodiversity.europa.eu/ecosystems/ecosystem-accounting', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd/target-2', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd/target-3b', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd/target-3a', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-020d736c-5304-4fb4-8744-ea53dc13ca9a', 'http://biodiversity.europa.eu/case-study-hub/CS%20Imperial%20eagle%20Spain', 'http://biodiversity.europa.eu/case-study-hub/CS%20Water%20courses%20Germany', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd/target-1', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd/target-4', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd/target-5', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd/target-6', 'http://biodiversity.europa.eu/policy/eu-6th-national-report-to-the-cbd/headline-target', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/pacoveragejan2021.png', 'http://biodiversity.europa.eu/protected-areas/other-effective-area-based-conservation-measures', 'http://biodiversity.europa.eu/protected-areas/other-effective-area-based-conservation-measures/final_report_oecms_in_eu_submitted_2021031.pdf', 'http://biodiversity.europa.eu/protected-areas/final_report_oecms_in_eu_submitted_2021031.pdf', 'http://biodiversity.europa.eu/protected-areas/final_report_oecms_in_eu_submitted_2021031_annex.pdf', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-9c8084f1-e89c-424e-9290-17266a5ceb31', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/pacoveragemarch2021.png', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-b3b0fe06-8d18-43ff-b7b2-9d803bca49b3', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-393a6a2b-c4e9-44bd-a170-386cf75933aa', 'http://biodiversity.europa.eu/case-study-hub', 'http://biodiversity.europa.eu/case-study-hub/CS-brown-bears-Italy/clipboard-cb58db46-9af1-408d-b3c0-686ed4769476', 'http://biodiversity.europa.eu/climate-change-distress.jpg', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/agroecosystems.png', 'http://biodiversity.europa.eu/topics', 'http://biodiversity.europa.eu/policy/globalpolicy.png', 'http://biodiversity.europa.eu/image-1.png', 'http://biodiversity.europa.eu/data/habitat-composition-by-group', 'http://biodiversity.europa.eu/data/conservation-status-habitats-directive', 'http://biodiversity.europa.eu/data/conservation-status-by-group', 'http://biodiversity.europa.eu/data/protected-species-composition', 'http://biodiversity.europa.eu/data/conservation-status-by-taxa', 'http://biodiversity.europa.eu/data/protected-species-least-present', 'http://biodiversity.europa.eu/data/protected-species-in-most-sites', 'http://biodiversity.europa.eu/data/protected-species-endemic-to-a-country', 'http://biodiversity.europa.eu/data/protected-species-endemic-counter', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/common-international-classification-of-ecosystem-services-cices', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/ecosystem-services-categories', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/reference-data-for-ecosystem-mapping', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/maes-green.png', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/maes-yellow.png', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/maes-red.png', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/maes-gray.png', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/indicators-of-ecosystem-condition', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/crosswalks-between-european-marine-habitat-typologies_10-04-14_v3.pdf', 'http://biodiversity.europa.eu/data/ecosystem.csv', 'http://biodiversity.europa.eu/policy/clipboard-9ef19091-f674-4820-afc1-a5a29c1e5418', 'http://biodiversity.europa.eu/protected-areas/future/clipboard-f8d80e32-d95e-4557-83eb-69df6989fa5d', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-247a8d31-71f0-4a31-9a59-35b81c7d83a0', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/2016-05-11-14-14-54.jpg', 'http://biodiversity.europa.eu/topics/case-studies/black-stork-in-hungary', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/map_countries_maes_20160107.png', 'http://biodiversity.europa.eu/policy/clipboard-7799c4f9-9c18-463f-aa17-fff453505dc6', 'http://biodiversity.europa.eu/policy/clipboard-65ac455a-9d4d-410d-81be-6d0f05a6aefe', 'http://biodiversity.europa.eu/policy/clipboard-f56b7180-aec8-463e-b60e-1e3043e92364', 'http://biodiversity.europa.eu/copy_of_maes_ver3.png', 'http://biodiversity.europa.eu/roe-deer-2615377_1920-1.jpg', 'http://biodiversity.europa.eu/roe-deer-2615377_1920-3.jpg', 'http://biodiversity.europa.eu/roe-deer-2615377_1920-6.jpg', 'http://biodiversity.europa.eu/roe-deer-2615377_1920-7.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-concepts', 'http://biodiversity.europa.eu/green-infrastructure/gi-policy-instruments', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors', 'http://biodiversity.europa.eu/green-infrastructure/cost-and-benefits/green-infrastructure.png', 'http://biodiversity.europa.eu/protected-areas/introduction/libelle.png', 'http://biodiversity.europa.eu/protected-areas/protected-species-habitats/clipboard-6714e8e6-5138-4025-84c4-1981c03f873e', 'http://biodiversity.europa.eu/protected-areas/protected-species-habitats/clipboard-fc8aec9a-0572-4154-8412-c44c3e675a36',
    #'http://biodiversity.europa.eu/protected-areas/protected-species-habitats/clipboard-83268bba-a784-4bd4-9353-3e0981c98947', 'http://biodiversity.europa.eu/topics/green-infrastructure.bmp', 'http://biodiversity.europa.eu/topics/threats-pressures/climate-change', 'http://biodiversity.europa.eu/countries', 'http://biodiversity.europa.eu/catalogue', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/agri_woman_esengl-yavuz.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/agri_woman_esengl-yavuz-1.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/forestry_ermanno-gianneschi.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/meanders_suleyman-uzumcu.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/leisure_erika-zolli.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/leisure_erika-zolli-1.jpg', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-sectors/bike_roberto-tavazzani.jpg', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/growth_sea.png', 'http://biodiversity.europa.eu/green-infrastructure/cost-and-benefits/clipboard-c2640442-9feb-4b02-af76-5334e342d4ee', 'http://biodiversity.europa.eu/green-infrastructure/clipboard-e116742b-7cb8-4758-8bc6-71a8d5e4fc43', 'http://biodiversity.europa.eu/policy/circle.png', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-0196886f-8f85-4888-a833-c4d53a321b6a', 'http://biodiversity.europa.eu/roe-deer-2615377_1920.jpg', 'http://biodiversity.europa.eu/roe-deer-2615377_1920-2.jpg', 'http://biodiversity.europa.eu/roe-deer-2615377_1920-4.jpg', 'http://biodiversity.europa.eu/roe-deer-2615377_1920-5.jpg', 'http://biodiversity.europa.eu/green-infrastructure/typology-of-gi', 'http://biodiversity.europa.eu/green-infrastructure/cost-and-benefits', 'http://biodiversity.europa.eu/green-infrastructure/cost-and-benefits/28692804013_c5454b0150_o-1.jpg', 'http://biodiversity.europa.eu/green-infrastructure/key-documents', 'http://biodiversity.europa.eu/green-infrastructure/gi-related-concepts/green-infrastructure_gi.png', 'http://biodiversity.europa.eu/case-study-hub/CS-brown-bears-Italy', 'http://biodiversity.europa.eu/case-study-hub/CS-brown-bears-Italy/clipboard-7ca1d10d-a520-44b1-86ab-74a48f67faab', 'http://biodiversity.europa.eu/countries/cyprus/maes', 'http://biodiversity.europa.eu/countries/cyprus', 'http://biodiversity.europa.eu/policy/clipboard-12badc7f-cb08-409d-8f02-4184cfab02d0', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/typology-of-ecosystems', 'http://biodiversity.europa.eu/protected-areas/management/clipboard-62df15be-3f61-4bf7-a635-fdc09fba9b8e', 'http://biodiversity.europa.eu/fp-slide.jpg', 'http://biodiversity.europa.eu/fp-slide-1.jpg', 'http://biodiversity.europa.eu/fp-slide-2.jpg', 'http://biodiversity.europa.eu/green-infrastructure', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-d7f06dee-d2f8-4295-8659-d8db6c449025', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/eu-assessment-report-small.png', 'http://biodiversity.europa.eu/image-3.png', 'http://biodiversity.europa.eu/image-5.png', 'http://biodiversity.europa.eu/image-7.png', 'http://biodiversity.europa.eu/image-2.jpg', 'http://biodiversity.europa.eu/image-5.jpg', 'http://biodiversity.europa.eu/track', 'http://biodiversity.europa.eu/track/streamlined-european-biodiversity-indicators', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/biogeoregionschart.png', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-20126155-f7b9-4d8e-ac5b-a64c76e4b73d', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-2835f586-fbff-4a93-ba79-2ce8b055fddd', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-201d1373-9149-4398-83b9-7d112848fc81', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/maes_papercentage.png', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-b48640d1-97cf-4f66-b2a5-5ac2be010eb5', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-9b52caed-2aa8-4b91-9022-c7ce25249362', 'http://biodiversity.europa.eu/protected-areas/size/clipboard-809f714f-985f-453d-91d7-133280821397', 'http://biodiversity.europa.eu/protected-areas/connectivity/clipboard-bb51f2a7-6930-4076-86b2-ea15b66f99ee', 'http://biodiversity.europa.eu/protected-areas/connectivity/clipboard-fa6adc84-8184-466c-9dbb-3642bbe95d01', 'http://biodiversity.europa.eu/protected-areas/connectivity/clipboard-84f8a8e9-0fea-44f3-b2e6-2abe7b6f9e67', 'http://biodiversity.europa.eu/protected-areas/connectivity/ch3keymessages.png', 'http://biodiversity.europa.eu/protected-areas/connectivity/ch4keymessages.png', 'http://biodiversity.europa.eu/protected-areas/protected-species-habitats/clipboard-4f1745e3-e993-4f37-b848-ea09233e1c96', 'http://biodiversity.europa.eu/ecosystems/clipboard-4d8cc3c8-175c-49c5-ab97-b75af1ef3555', 'http://biodiversity.europa.eu/ecosystems/clipboard-6230b6fd-3686-4495-be38-9dd82d5ae96f', 'http://biodiversity.europa.eu/green-infrastructure/clipboard-e70ad3ca-1d9b-49f4-93fa-2cfcea962aa9', 'http://biodiversity.europa.eu/green-infrastructure/clipboard-d8ebcf8f-326d-4bc1-a5a6-1bc5b9a1ff2f', 'http://biodiversity.europa.eu/countries/austria/clipboard-32535e4b-614c-4330-9391-20aaf55ee15e', 'http://biodiversity.europa.eu/data/maesmockup_mapviewer_overall_eco.pdf', 'http://biodiversity.europa.eu/policy/clipboard-f871136f-d247-4308-824f-69dfbc4427cf', 'http://biodiversity.europa.eu/policy/clipboard-665001ba-3691-496c-bb3b-60f44d0432d6', 'http://biodiversity.europa.eu/data', 'http://biodiversity.europa.eu/data/landcover_use_bio.csv', 'http://biodiversity.europa.eu/data/statistics_ecosystems_all_eu27-bycountry-eu27.csv', 'http://biodiversity.europa.eu/data/stats_size_sea.csv', 'http://biodiversity.europa.eu/data/stats_size_land.csv', 'http://biodiversity.europa.eu/protected-areas/size/clipboard-18a8be00-2e84-4d56-82e7-92319d473df5', 'http://biodiversity.europa.eu/biodiversity-data/countries-outside-of-eu', 'http://biodiversity.europa.eu/ecosystems/agroecosystems', 'http://biodiversity.europa.eu/ecosystems/urban-ecosystems', 'http://biodiversity.europa.eu/ecosystems/wetlands', 'http://biodiversity.europa.eu/ecosystems/rivers-and-lakes', 'http://biodiversity.europa.eu/ecosystems/marine', 'http://biodiversity.europa.eu/ecosystems/forest', 'http://biodiversity.europa.eu/ecosystems/heathlands-shrubs-and-sparsely-vegetated-lands', 'http://biodiversity.europa.eu/protected-areas/management', 'http://biodiversity.europa.eu/protected-areas/future', 'http://biodiversity.europa.eu/data/top-5-pressures-in-sites', 'http://biodiversity.europa.eu/data/top-5-sites', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/correspondence-between-corine-land-cover-classes-and-ecosystem-types', 'http://biodiversity.europa.eu/protected-areas/introduction/parepintropic1.png', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/eu-assessment-report-small.jpg', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/capture.jpg', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/esmeralda.png', 'http://biodiversity.europa.eu/data/conservation-status-good-by-habitats-directive', 'http://biodiversity.europa.eu/data/conservation-status-poor-by-habitats-directive', 'http://biodiversity.europa.eu/data/conservation-status-bad-by-habitats-directive', 'http://biodiversity.europa.eu/data/conservation-status-unknown-by-habitats-directive', 'http://biodiversity.europa.eu/legal-and-privacy-notice', 'http://biodiversity.europa.eu/legal-and-privacy-notice/bise-specific-privacy-statement', 'http://biodiversity.europa.eu/data/mesageonpamakeup.csv', 'http://biodiversity.europa.eu/data/conservation-status-good-for-species', 'http://biodiversity.europa.eu/data/conservation-status-poor-species', 'http://biodiversity.europa.eu/data/conservation-status-bad-species', 'http://biodiversity.europa.eu/conservation-status-unknown-species', 'http://biodiversity.europa.eu/protected-areas/protected-species-habitats/clipboard-465b24e1-8cf9-46b5-a80e-ba80ba6a31e8', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/esmeralda-1.png', 'http://biodiversity.europa.eu/countries/hungary/maes-1', 'http://biodiversity.europa.eu/countries/hungary/maes-1/copy_of_iamge1.png', 'http://biodiversity.europa.eu/countries/hungary/maes-1/image2.png', 'http://biodiversity.europa.eu/countries/hungary/maes-1/image3.png', 'http://biodiversity.europa.eu/countries/hungary/maes-1/image4.jpg', 'http://biodiversity.europa.eu/protected-areas/protected-species-habitats', 'http://biodiversity.europa.eu/image-1-1.png', 'http://biodiversity.europa.eu/image-2.png', 'http://biodiversity.europa.eu/image-4.png', 'http://biodiversity.europa.eu/image-6.png', 'http://biodiversity.europa.eu/image-8.png', 'http://biodiversity.europa.eu/policy', 'http://biodiversity.europa.eu/policy/mtr_country_reports.docx', 'http://biodiversity.europa.eu/policy/clipboard-ca5adc6a-0a2c-4661-96d1-273fdbbf140f', 'http://biodiversity.europa.eu/policy/clipboard-26f24cdb-a8f0-435d-a995-c34263ca58a7', 'http://biodiversity.europa.eu/data/statsforcountryprofile_bise.csv', 'http://biodiversity.europa.eu/policy/eumessage.png', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/pacoverageoct2020.png', 'http://biodiversity.europa.eu/data/top-5-sites-with-most-species',
    #'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-3390e49a-bc64-40f3-a6a7-490b867cc8b6', 'http://biodiversity.europa.eu/protected-areas/introduction', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity', 'http://biodiversity.europa.eu/protected-areas/size', 'http://biodiversity.europa.eu/protected-areas/connectivity', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/crosswalksbetweeneuropeanmarinehabitattypologies_dec2018.pdf', 'http://biodiversity.europa.eu/countries/austria/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/austria/maes', 'http://biodiversity.europa.eu/countries/austria/green-infrastructure', 'http://biodiversity.europa.eu/countries/austria', 'http://biodiversity.europa.eu/countries/belgium/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/belgium/maes', 'http://biodiversity.europa.eu/countries/belgium/green-infrastructure', 'http://biodiversity.europa.eu/countries/belgium', 'http://biodiversity.europa.eu/countries/bulgaria/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/bulgaria/maes', 'http://biodiversity.europa.eu/countries/bulgaria/green-infrastucture', 'http://biodiversity.europa.eu/countries/bulgaria', 'http://biodiversity.europa.eu/countries/croatia/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/croatia/maes', 'http://biodiversity.europa.eu/countries/croatia/green-infrastructure', 'http://biodiversity.europa.eu/countries/croatia', 'http://biodiversity.europa.eu/countries/czechia/maes', 'http://biodiversity.europa.eu/countries/czechia/green-infrastructure', 'http://biodiversity.europa.eu/countries/czechia', 'http://biodiversity.europa.eu/countries/denmark/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/denmark/maes', 'http://biodiversity.europa.eu/countries/denmark/green-infrastructure', 'http://biodiversity.europa.eu/countries/denmark', 'http://biodiversity.europa.eu/countries/estonia/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/estonia/maes', 'http://biodiversity.europa.eu/countries/estonia', 'http://biodiversity.europa.eu/countries/finland/maes', 'http://biodiversity.europa.eu/countries/finland/green-infrastructure', 'http://biodiversity.europa.eu/countries/finland', 'http://biodiversity.europa.eu/countries/france/maes/fr_maes2.png', 'http://biodiversity.europa.eu/countries/france/maes', 'http://biodiversity.europa.eu/countries/france/green-infrastructure', 'http://biodiversity.europa.eu/countries/france', 'http://biodiversity.europa.eu/countries/germany/maes', 'http://biodiversity.europa.eu/countries/germany/green-infrastructure', 'http://biodiversity.europa.eu/countries/germany', 'http://biodiversity.europa.eu/countries/greece/maes', 'http://biodiversity.europa.eu/countries/greece/green-infrastructure', 'http://biodiversity.europa.eu/countries/greece', 'http://biodiversity.europa.eu/countries/hungary/green-infrastructure', 'http://biodiversity.europa.eu/countries/hungary', 'http://biodiversity.europa.eu/countries/ireland/maes', 'http://biodiversity.europa.eu/countries/ireland/green-infrastructure', 'http://biodiversity.europa.eu/countries/ireland', 'http://biodiversity.europa.eu/countries/latvia/green-infrastructure', 'http://biodiversity.europa.eu/countries/latvia/maes', 'http://biodiversity.europa.eu/countries/latvia', 'http://biodiversity.europa.eu/countries/italy/maes', 'http://biodiversity.europa.eu/countries/italy/green-infrastructure', 'http://biodiversity.europa.eu/countries/italy', 'http://biodiversity.europa.eu/countries/lithuania/maes', 'http://biodiversity.europa.eu/countries/lithuania/green-infrastructure', 'http://biodiversity.europa.eu/countries/lithuania', 'http://biodiversity.europa.eu/countries/luxembourg/maes', 'http://biodiversity.europa.eu/countries/luxembourg/green-infrastructure', 'http://biodiversity.europa.eu/countries/luxembourg', 'http://biodiversity.europa.eu/countries/malta/maes', 'http://biodiversity.europa.eu/countries/malta/green-infrastructure', 'http://biodiversity.europa.eu/countries/malta', 'http://biodiversity.europa.eu/countries/netherlands/maes', 'http://biodiversity.europa.eu/countries/netherlands/green-infrastructure', 'http://biodiversity.europa.eu/countries/netherlands', 'http://biodiversity.europa.eu/countries/poland/maes', 'http://biodiversity.europa.eu/countries/poland/green-infrastructure', 'http://biodiversity.europa.eu/countries/poland', 'http://biodiversity.europa.eu/countries/portugal/maes', 'http://biodiversity.europa.eu/countries/portugal/green-infrastructure', 'http://biodiversity.europa.eu/countries/portugal', 'http://biodiversity.europa.eu/countries/romania/maes', 'http://biodiversity.europa.eu/countries/romania/green-infrastructure', 'http://biodiversity.europa.eu/countries/romania', 'http://biodiversity.europa.eu/countries/slovakia/maes', 'http://biodiversity.europa.eu/countries/slovakia/green-infrastructure', 'http://biodiversity.europa.eu/countries/slovakia', 'http://biodiversity.europa.eu/countries/slovenia/maes', 'http://biodiversity.europa.eu/countries/slovenia/green-infrastructure', 'http://biodiversity.europa.eu/countries/slovenia', 'http://biodiversity.europa.eu/countries/spain/maes', 'http://biodiversity.europa.eu/countries/spain/green-infrastructure', 'http://biodiversity.europa.eu/countries/spain', 'http://biodiversity.europa.eu/countries/sweden/maes', 'http://biodiversity.europa.eu/countries/sweden/green-infrastructure', 'http://biodiversity.europa.eu/countries/sweden', 'http://biodiversity.europa.eu/countries/ireland/eu-biodiversity-strategy-to-2020', 'http://biodiversity.europa.eu/countries/czechia/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/finland/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/france/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/germany/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/greece/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/hungary/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/latvia/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/italy/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/lithuania/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/luxembourg/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/malta/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/netherlands/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/poland/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/portugal/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/romania/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/slovakia/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/slovenia/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/spain/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/countries/sweden/eu-biodiversity-strategy', 'http://biodiversity.europa.eu/image-1.jpg', 'http://biodiversity.europa.eu/image-4.jpg', 'http://biodiversity.europa.eu/image-8.jpg', 'http://biodiversity.europa.eu/protected-areas/coverage-representativity/clipboard-b903cff7-5528-4173-8254-543a7ace169b', 'http://biodiversity.europa.eu/front-page', 'http://biodiversity.europa.eu/protected-areas/management/clipboard-61d7eddc-6b11-4562-bec1-67f388796433', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1/eu-biodiv-strategy-cif.pdf', 'http://biodiversity.europa.eu/forest.jpg', 'http://biodiversity.europa.eu/data/countries-protected-areas-statistics', 'http://biodiversity.europa.eu/protected-areas', 'http://biodiversity.europa.eu/threats/climate-change', 'http://biodiversity.europa.eu/threats/invasive-species', 'http://biodiversity.europa.eu/threats/fragmentation', 'http://biodiversity.europa.eu/threats/land-use-change', 'http://biodiversity.europa.eu/threats/pollution', 'http://biodiversity.europa.eu/threats/overexploitation', 'http://biodiversity.europa.eu/threats', 'http://biodiversity.europa.eu/flagship-projects', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/heathland-and-shrubs', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/sparsely-vegetated-land', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/islands/islands_ver2_forweb.jpg', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/islands', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/wetlands', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/marine', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/mountains/mountain-massifs.png', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/mountains', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/urban', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/cropland', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types/rivers-and-lakes', 'http://biodiversity.europa.eu/ecosystems/ecosystem-types', 'http://biodiversity.europa.eu/ecosystems/mapping-and-assessment-of-ecosystems-and-their-services-maes-1', 'http://biodiversity.europa.eu/ecosystems', 'http://biodiversity.europa.eu/data-catalogue', 'http://biodiversity.europa.eu/ecosystems/ecosystem-accounting/spatial-nutrient-accounts_summary-document_dec-2020_v-0-98_final-rev_01-02-21.pdf', 'http://biodiversity.europa.eu/ecosystems/ecosystem-accounting/eea-ecosystem-extent_analytical-report_final-for-publication_30-03-21.docx', 'http://biodiversity.europa.eu/extent-account-per-country_eea-39_2018.xlsx', 'http://biodiversity.europa.eu/ecosystems/ecosystem-accounting/analytical-report-on-european-ecosystem-extent-accounts-2000_2018.docx', 'http://biodiversity.europa.eu/ecosystems/ecosystem-accounting/eo4ea_supporting-note_2020-copernicus-database_final-draft_12-12-20.pdf',
    #'http://biodiversity.europa.eu/ecosystems/ecosystem-accounting/eo4ea_copernicus-database_2020_v2_nov-2020.xlsx']
    print("1 ", clean_urls1)
    print("2 ", clean_urls2)
    print_type(clean_urls1)
    print_type(clean_urls2)

    for url in clean_urls2:
        print("trigger_url:", url)
        task_id = "fetch_url_" + helpers.nicename(url)
        print("task_id:", task_id)
        BulkTriggerDagRunOperator(
            task_id=task_id,
            trigger_dag_id="fetch_url",
            conf={"url": url, "maintainer_email": "tibi@example.com"},
        )

    # trigger_fetch_for_urls(urls)


crawl_website_dag = crawl_plonerestapi_website()


# clean_urls = [
#     "http://biodiversity.europa.eu/protected-areas/life-nature-and-biodiversity-projects"
# ]
# trigger_fetch_for_urls(urls)

# trigger_dagrun.TriggerDagRunOperator(
#        task_id="trigger_fetch_url2",
#        trigger_dag_id="fetch_url",
#        conf={"url": "url3", "maintainer_email": "tibi@example.com"},
#    )


#  {'conf': <airflow.configuration.AirflowConfigParser object at 0x7f84bce49da0>,
#  'dag': <DAG: crawl_plonerestapi_website>,
#  'dag_run': <DagRun crawl_plonerestapi_website @ 2021-05-26 04:24:22.463409+00:00: manual__2021-05-26T04:24:22.453381+00:00, externally triggered: True>,
#  'ds': '2021-05-26',
#  'ds_nodash': '20210526',
#  'execution_date': DateTime(2021, 5, 26, 4, 24, 22, 463409, tzinfo=Timezone('+00:00')),
#  'inlets': [],
#  'macros': <module 'airflow.macros' from '/home/airflow/.local/lib/python3.6/site-packages/airflow/macros/__init__.py'>,
#  'next_ds': '2021-05-26',
#  'next_ds_nodash': '20210526',
#  'next_execution_date': DateTime(2021, 5, 26, 4, 24, 22, 463409, tzinfo=Timezone('+00:00')),
#  'outlets': [],
#  'params': {'maintainer_email': 'tibi@example.com',
#             'website_url': 'https://biodiversity.europa.eu'},
#  'prev_ds': '2021-05-26',
#  'prev_ds_nodash': '20210526',
#  'prev_execution_date': DateTime(2021, 5, 26, 4, 24, 22, 463409, tzinfo=Timezone('+00:00')),
#  'prev_execution_date_success': <Proxy at 0x7f84b1b19948 with factory <function TaskInstance.get_template_context.<locals>.<lambda> at 0x7f84b1b37ea0>>,
#  'prev_start_date_success': <Proxy at 0x7f84b1e6ca08 with factory <function TaskInstance.get_template_context.<locals>.<lambda> at 0x7f84b1ecde18>>,
#  'run_id': 'manual__2021-05-26T04:24:22.453381+00:00',
#  'task': <Task(PythonOperator): trigger_fetch_for_urls>,
#  'task_instance': <TaskInstance: crawl_plonerestapi_website.trigger_fetch_for_urls 2021-05-26T04:24:22.463409+00:00 [running]>,
#  'task_instance_key_str': 'crawl_plonerestapi_website__trigger_fetch_for_urls__20210526',
#  'templates_dict': None,
#  'test_mode': False,
#  'ti': <TaskInstance: crawl_plonerestapi_website.trigger_fetch_for_urls 2021-05-26T04:24:22.463409+00:00 [running]>,
#  'tomorrow_ds': '2021-05-27',
#  'tomorrow_ds_nodash': '20210527',
#  'ts': '2021-05-26T04:24:22.463409+00:00',
#  'ts_nodash': '20210526T042422',
#  'ts_nodash_with_tz': '20210526T042422.463409+0000',
#  'var': {'json': None, 'value': None},
#  'yesterday_ds': '2021-05-25',
#  'yesterday_ds_nodash': '20210525'}
# [2021-05-26 04:24:45,042] {logging_mixin.py:104} INFO - kwargs
# [2021-05-26 04:24:45,043] {logging_mixin.py:104} INFO - {'conf': <airflow.configuration.AirflowConfigParser object at 0x7f84bce49da0>,
#  'dag': <DAG: crawl_plonerestapi_website>,
#  'dag_run': <DagRun crawl_plonerestapi_website @ 2021-05-26 04:24:22.463409+00:00: manual__2021-05-26T04:24:22.453381+00:00, externally triggered: True>,
#  'ds': '2021-05-26',
#  'ds_nodash': '20210526',
#  'execution_date': DateTime(2021, 5, 26, 4, 24, 22, 463409, tzinfo=Timezone('+00:00')),
#  'inlets': [],
#  'macros': <module 'airflow.macros' from '/home/airflow/.local/lib/python3.6/site-packages/airflow/macros/__init__.py'>,
#  'next_ds': '2021-05-26',
#  'next_ds_nodash': '20210526',
#  'next_execution_date': DateTime(2021, 5, 26, 4, 24, 22, 463409, tzinfo=Timezone('+00:00')),
#  'outlets': [],
#  'params': {'maintainer_email': 'tibi@example.com',
#             'website_url': 'https://biodiversity.europa.eu'},
#  'prev_ds': '2021-05-26',
#  'prev_ds_nodash': '20210526',
#  'prev_execution_date': DateTime(2021, 5, 26, 4, 24, 22, 463409, tzinfo=Timezone('+00:00')),
#  'prev_execution_date_success': <Proxy at 0x7f84b1b19948 wrapping None at 0x7f84bfc84110 with factory <function TaskInstance.get_template_context.<locals>.<lambda> at 0x7f84b1b37ea0>>,
#  'prev_start_date_success': <Proxy at 0x7f84b1e6ca08 wrapping None at 0x7f84bfc84110 with factory <function TaskInstance.get_template_context.<locals>.<lambda> at 0x7f84b1ecde18>>,
#  'run_id': 'manual__2021-05-26T04:24:22.453381+00:00',
#  'task': <Task(PythonOperator): trigger_fetch_for_urls>,
#  'task_instance': <TaskInstance: crawl_plonerestapi_website.trigger_fetch_for_urls 2021-05-26T04:24:22.463409+00:00 [running]>,
#  'task_instance_key_str': 'crawl_plonerestapi_website__trigger_fetch_for_urls__20210526',
#  'templates_dict': None,
#  'test_mode': False,
#  'ti': <TaskInstance: crawl_plonerestapi_website.trigger_fetch_for_urls 2021-05-26T04:24:22.463409+00:00 [running]>,
#  'tomorrow_ds': '2021-05-27',
#  'tomorrow_ds_nodash': '20210527',
#  'ts': '2021-05-26T04:24:22.463409+00:00',
#  'ts_nodash': '20210526T042422',
#  'ts_nodash_with_tz': '20210526T042422.463409+0000',
#  'var': {'json': None, 'value': None},
#  'yesterday_ds': '2021-05-25',
#  'yesterday_ds_nodash': '20210525'}
