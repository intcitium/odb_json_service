import shodan
import click
from apiserver.utils import get_datetime
from apiserver.models import OSINTModel as Models
from apiserver.blueprints.home.models import ODB
from apiserver.utils import SHODAN
api = shodan.Shodan(SHODAN)
"""
https://shodan.readthedocs.io/en/latest/tutorial.html
"""


class Shodan(ODB):

    def __init__(self, db_name="OSINT"):
        ODB.__init__(self, db_name, models=Models)

    def search(self, searchterm):
        """
        The provided string is used to search the database of banners in Shodan, with the additional option to provide
        filters inside the search query using a "filter:value" format. For example, the following search query would
        find Apache webservers located in Germany: "apache country:DE".
        :param searchterm:
        :return:
        """
        click.echo('[%s_Shodan_search] Starting search for %s' % (get_datetime(), searchterm))
        results = api.search(searchterm)
        click.echo('[%s_Shodan_search] Complete with %d items' % (get_datetime(), results["total"]))
        for r in results["matches"]:
            # Set up the Shodan Crawler node from the row
            if '_shodan' in r.keys():
                if 'id' in r["_shodan"].keys():
                    s_keys = ["crawler", "module", "id"]
                    s_node = {
                        "class_name": "Object",
                        "Category": "Shodan crawler",
                        "Ext_key": r["_shodan"]["id"],
                        "description": "Shodan crawler %s" % str(
                            r["_shodan"]).replace("'", "").replace('"', "").replace("{", "").replace("}", "")
                    }
                    for sk in s_keys:
                        if sk in r['_shodan'].keys():
                            s_node[sk] = r['_shodan'][sk]
                    # Create the Shodan Crawler Node
                    s_node = self.create_node(**s_node)
                    # Set up the device found
                    d_keys = ["ip", "os", "timestamp", "hash", "isp", "port", "info", "version", "product", "ip_str", "asn", "org"]
                    if 'ip_str' in r.keys() and 'port' in r.keys():
                        d_node = {
                            "class_name": "Object",
                            "Category": "Device",
                            "Ext_key": "%s:%s" % (r["ip_str"], r["port"])
                        }
                        for dk in d_keys:
                            if dk in r.keys():
                                d_node[dk] = r[dk]
                        # Create the Device found by the crawler
                        d_node = self.create_node(**d_node)
                        # Create the relationship
                        self.create_edge_new(
                            edgeType="Discovered",
                            fromNode=s_node["data"]["key"],
                            toNode=d_node["data"]["key"])
                        # Get the vulnerabilities
                        if 'vulns' in r.keys():
                            for v in r['vulns']:
                                v_ok = True
                                cve = self.client.command('''
                                select rid from index:Vulnerability_Ext_key where key = '%s'
                                ''' % v)
                                try:
                                    if len(cve) < 1:
                                        v_node = self.create_node(
                                            class_name="Vulnerability",
                                            Ext_key=v,
                                            description=r['vulns'][v]["summary"],
                                            source="Shodan",

                                        )["data"]["key"]
                                except Exception as e:
                                    click.echo('[%s_Shodan_search] Error with vulnerability node %s: %s' % (
                                    get_datetime(), str(e), v))
                                    v_ok = False
                                else:
                                    try:
                                        v_node = cve[0].oRecordData["rid"].get_hash()
                                    except:
                                        click.echo('[%s_Shodan_search] Error with vulnerability node %s: %s' % (
                                        get_datetime(), str(e), v))
                                        v_ok = False
                                if v_ok:
                                    self.create_edge_new(
                                        edgeType="Has",
                                        fromNode=d_node["data"]["key"],
                                        toNode=v_node
                                    )
                                    # Get the References for each vulnerability
                                    if "references" in r['vulns'][v]:
                                        try:
                                            for ref in r['vulns'][v]["references"]:
                                                ref_node = self.create_node(
                                                    class_name="Object",
                                                    Category="Vulnerability Reference",
                                                    Ext_key=ref,
                                                    source="Shodan",
                                                    description="Reference to %s" % v)["data"]["key"]
                                                self.create_edge_new(
                                                    edgeType="References",
                                                    fromNode=ref_node,
                                                    toNode=v_node
                                                )
                                        except Exception as e:
                                            click.echo('[%s_Shodan_search] Error with reference node %s: %s' % (
                                                get_datetime(), str(e), ref))
                        if 'location' in r.keys():
                            l_keys = ["country_name", "city", "longitude", "latitude"]
                            l_node = {"class_name": "Location"}
                            create = True
                            for lk in l_keys:
                                if r['location'][lk] != None:
                                    l_node[lk.capitalize()] = r['location'][lk]
                                else:
                                    create = False
                            if create:
                                l_node = self.create_node(**l_node)["data"]["key"]
                                self.create_edge_new(
                                    edgeType="LocatedAt",
                                    fromNode=d_node["data"]["key"],
                                    toNode=l_node
                                )
        return results

    def get_host(self, ip_address):
        try:
            click.echo('[%s_Shodan_get_host] Complete with %d items' % (get_datetime(), ip_address))

        except Exception as e:
            click.echo('[%s_Shodan_get_host] Complete with %d items' % (get_datetime(), ip_address))

