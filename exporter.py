"""Application exporter"""

import os
import time
from prometheus_client import start_http_server, Gauge, Enum
import requests
import re
from datetime import datetime, timezone

#https://github.com/forta-network/forta-core-go/blob/1db463db513fb7a735592a375bf06427ebacb031/clients/health/report.go#L16
def forta_status_code(code):
    match code:
        case "ok":
            return 0
        case "down":
            return 1
        case "failing":
            return 2     
        case "lagging":
            return 3
        case "info":
            return 4
        case _: #unknown
            return 5  

def chainid_to_network(chainid):
    match chainid:
        case 1:
            return "ethereum"
        case 56:
            return "bsc"
        case 137:
            return "polygon"
        case 43114:
            return "avalanche"
        case 42161:
            return "arbitrum"
        case 10:
            return "optimism"
        case 250:
            return "fantom"
        case _:
            return ""

def get_timestamp(dtstring):
    dt = datetime.strptime(dtstring, '%Y-%m-%dT%H:%M:%SZ')

    # convert datetime to time-aware timezone at UTC
    # so correct timestamp is returned
    dt = dt.replace(tzinfo=timezone.utc)

    # Return the time in seconds since the epoch 
    return dt.timestamp()

class AppMetrics:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, app_port=80, polling_interval_seconds=15, Scanner_address=""):
        self.app_port = app_port
        self.polling_interval_seconds = polling_interval_seconds
        self.scanner_address = Scanner_address

        # Prometheus metrics to collect

        self.forta_version = Gauge("forta_version", "Forta node version", ["forta_version"])
        self.forta_scanner_status = Gauge("forta_scanner_status", "Forta scanner status, 0 means ok", ["detail"])
        self.forta_scanner_block_height = Gauge("forta_scanner_block_height", "Forta scanner last block fed")
        self.forta_inspector_status = Gauge("forta_inspector_status", "Forta inspector status, 0 means ok", ["detail"])
        self.forta_json_rpc_status = Gauge("forta_json_rpc_status", "Forta json rpc status, 0 means ok", ["detail"])
        self.forta_supervisor_status = Gauge("forta_supervisor_status", "Forta supervisor status, 0 means ok", ["detail"])
        self.forta_updater_status = Gauge("forta_updater_status", "Forta updater status, 0 means ok", ["detail"])
        self.forta_agent_pool = Gauge("forta_agent_pool", "Number of Forta agent pool",["agent_lag_count"])
        self.forta_chainid = Gauge("forta_chainid", "Chain id of the chain forta node is running",["network"])
        self.forta_sla = Gauge("forta_sla", "SLA for the scanner address",["scanner_address"])

    def run_metrics_loop(self):
        """Metrics fetching loop"""

        while True:
            self.fetch()
            time.sleep(self.polling_interval_seconds)

    def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """

        # Fetch data from the contract
        try:
            #Fetch Scanner address SLA
            url=f"https://api.forta.network/stats/sla/scanner/{self.scanner_address}"
            sla_data = requests.get(url=url).json()
            self.forta_sla.labels(scanner_address=self.scanner_address).set(sla_data['statistics']['avg'])

        except Exception as e:
            print(f"Error trying to access the SLA data on {url} with error:" + str(e))

        try:
            #Fetch forta node health data
            url="http://localhost:8090/health"
            health_data = requests.get(url=url).json()

            #   {
            #     "name": "forta.version",
            #     "status": "info",
            #     "details": "v0.5.6"
            #   }
            detail=[x["details"] for x in health_data if x["name"] == "forta.version"][0]
            self.forta_version.labels(forta_version=detail).set(1)

            #   {
            #     "name": "forta.container.forta-scanner.summary",
            #     "status": "ok",
            #     "details": "at block 15514261." | "at block 49216362. trace api (trace_block) is failing with error 'Invalid block for tracing'."
            #   },
            status=[x["status"] for x in health_data if x["name"] == "forta.container.forta-scanner.summary"][0]
            detail=[x["details"] for x in health_data if x["name"] == "forta.container.forta-scanner.summary"][0]

            #remove 'at block 15514261.'
            detail=re.sub(r'at block \d+\. ', '', detail)

            if status != "ok":
                self.forta_scanner_status.labels(detail=detail).set(forta_status_code(status))
            else:
                self.forta_scanner_status.labels(detail="").set(forta_status_code(status))
 
            #   {
            #     "name": "forta.container.forta-scanner.service.block-feed.last-block",
            #     "status": "info",
            #     "details": "15514261"
            #   },
            detail=[x["details"] for x in health_data if x["name"] == "forta.container.forta-scanner.service.block-feed.last-block"][0]
            self.forta_scanner_block_height.set(int(detail))

            #   {
            #     "name": "forta.container.forta-inspector",
            #     "status": "ok",
            #     "details": "running"
            #   },
            status=[x["status"] for x in health_data if x["name"] == "forta.container.forta-inspector"][0]
            detail=[x["details"] for x in health_data if x["name"] == "forta.container.forta-inspector"][0]
            self.forta_inspector_status.labels(detail=detail).set(forta_status_code(status))

            #   {
            #     "name": "forta.container.forta-json-rpc",
            #     "status": "ok",
            #     "details": "running"
            #   }
            status=[x["status"] for x in health_data if x["name"] == "forta.container.forta-json-rpc"][0]
            detail=[x["details"] for x in health_data if x["name"] == "forta.container.forta-json-rpc"][0]
            self.forta_json_rpc_status.labels(detail=detail).set(forta_status_code(status))

            #   {
            #     "name": "forta.container.forta-supervisor",
            #     "status": "ok",
            #     "details": "running"
            #   }
            status=[x["status"] for x in health_data if x["name"] == "forta.container.forta-supervisor"][0]
            detail=[x["details"] for x in health_data if x["name"] == "forta.container.forta-supervisor"][0]
            self.forta_supervisor_status.labels(detail=detail).set(forta_status_code(status))


            #   {
            #     "name": "forta.container.forta-updater",
            #     "status": "ok",
            #     "details": "running"
            #   },
            status=[x["status"] for x in health_data if x["name"] == "forta.container.forta-updater"][0]
            detail=[x["details"] for x in health_data if x["name"] == "forta.container.forta-updater"][0]
            self.forta_updater_status.labels(detail=detail).set(forta_status_code(status))

            #   {
            #     "name": "forta.container.forta-scanner.service.agent-pool.agents.total",
            #     "status": "ok",
            #     "details": "24"
            #   },
            #   {
            #     "name": "forta.container.forta-scanner.service.agent-pool.agents.lagging",
            #     "status": "info",
            #     "details": "0"
            #   },
            detail=[x["details"] for x in health_data if x["name"] == "forta.container.forta-scanner.service.agent-pool.agents.total"][0]
            lag_count=[x["details"] for x in health_data if x["name"] == "forta.container.forta-scanner.service.agent-pool.agents.lagging"][0]
            self.forta_agent_pool.labels(agent_lag_count=lag_count).set(int(detail))

            #   {
            #     "name": "forta.container.forta-inspector.service.inspector.scan-api.chain-id",
            #     "status": "info",
            #     "details": "1"
            # } 
            detail=[x["details"] for x in health_data if x["name"] == "forta.container.forta-inspector.service.inspector.scan-api.chain-id"][0]
            self.forta_chainid.labels(network=chainid_to_network(int(detail))).set(int(detail))

        except Exception as e:
            print(f"Error trying to access the health data on {url} with error:" + str(e))
            
def main():
    """Main entry point"""

    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "15"))
    app_port = int(os.getenv("APP_PORT", "80"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))
    ScannerAddress = os.getenv("SCANNER_ADDRESS", "")

    print("Forta Exporter started and now listening on port "+str(exporter_port))

    app_metrics = AppMetrics(
        app_port=app_port,
        polling_interval_seconds=polling_interval_seconds,
        Scanner_address=ScannerAddress
    )
    start_http_server(exporter_port)
    app_metrics.run_metrics_loop()

if __name__ == "__main__":
    main()
