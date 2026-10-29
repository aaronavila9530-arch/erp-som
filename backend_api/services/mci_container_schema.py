"""MCI-only container narrative fields, independent of the MSL Excel contract."""
TITLES = {
    'introduction': 'INTRODUCTION', 'purpose': 'Purpose',
    'instructions': 'Instructions', 'representatives': 'Representatives',
    'particulars': 'PARTICULARS', 'timesheet': 'EXTRACT TIME SHEET',
    'damage': 'DETAILS OF DAMAGE / SHORTAGE (IF ANY) OR INSPECTION CAUSE',
    'remarks': 'REMARKS', 'conclusion': 'CONCLUSION',
    'enclosure': 'SURVEY LINK PICTURES', 'attachments': 'ENCLOSURES',
}
GROUPS = {'introduction': ('purpose', 'instructions', 'representatives'),
          'particulars': (), 'timesheet': (), 'damage': (), 'remarks': (),
          'conclusion': (), 'enclosure': (), 'attachments': ()}
FIELDS = {
    'cargo': 'Cargo', 'quantity': 'Quantity', 'gross_weight': 'Gross weight',
    'shipper': 'Shipper', 'consignee': 'Consignee', 'loading_port': 'Port of loading',
    'discharge_port': 'Port of discharge', 'vessel_voyage': 'Vessel / voyage',
    'opening_at': 'Container opening', 'arrival_at': 'Surveyor arrived',
    'survey_place': 'Survey place', 'on_behalf_of': 'On behalf of',
    'receiver_representative': 'Receiver representative', 'surveyor': 'Surveyor / signatory',
}
