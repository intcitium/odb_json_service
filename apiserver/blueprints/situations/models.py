from apiserver.blueprints.simulations.models import Pole
import datetime

class SituationsDB(Pole):

    def __init__(self, db_name="POLE"):
        Pole.__init__(self, db_name)
        self.db_name = db_name

    def model_message(self, oRecord):

        if 'FirstName' in oRecord.keys():
            message = "%s %s was born on %s in %s" % (
                oRecord['FirstName'],
                oRecord['LastName'],
                datetime.datetime.strftime(oRecord['DateOfBirth'], "%d %B, %Y"),
                oRecord['PlaceOfBirth']
            )

        return message

    def get_risks(self, LastName):
        return self.get_node(class_name="Person", val=LastName, var="LastName")

