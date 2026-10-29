"""MCI narrative workflow with Logistics Supervision-specific sections."""
TITLES = {
    'instructions':'INSTRUCTIONS, SCOPE AND METHODOLOGY', 'work':'Work performed',
    'limitations':'Main limitations of this report', 'chronology':'Time sheet',
    'representatives':'Representatives', 'particulars':'VESSEL PARTICULARS',
    'process':'SUPERVISION PROCESS', 'findings':'SURVEY FINDINGS',
    'documentary':'Documentary findings', 'operational':'Operational control findings',
    'incidents':'Incidents', 'conclusion':'CONCLUSION', 'enclosure':'ENCLOSURE',
}
GROUPS = {'instructions':('work','limitations','chronology','representatives'),
          'particulars':(), 'process':(), 'findings':('documentary','operational','incidents'),
          'conclusion':(), 'enclosure':()}
FIELDS = {
    'imo':'IMO', 'length_and_tonnage':'Length overall and tonnage', 'cargo':'Cargo',
    'flag_port_registry':'Flag / port of registry', 'grt':'GRT', 'nrt':'NRT',
    'build_year':'Year built', 'period_start':'Period investigated - from',
    'period_end':'Period investigated - to', 'issue_date':'Date of issue',
    'arrival_date':'Arrival date', 'inspection_date':'Inspection date',
    'supervision_completed_date':'Supervision completed', 'report_status':'Report status',
    'master':'Master', 'chief_officer':'Chief officer', 'surveyor':'Surveyor / signatory',
}
