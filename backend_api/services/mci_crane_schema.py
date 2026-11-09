"""Crane-specific optional sections within the existing MCI report format."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from services.crane_web_fields import POINTS, OPTIONS

TITLES={'instructions':'INSTRUCTIONS, SCOPE AND METHODOLOGY','crane_intro':'Introduction',
        'gear':'CRANES GEAR SURVEY','gear_condition':'Condition','gear_wires':'Hoisting and luffing wires',
        'gear_sheaves':'Sheaves','gear_operability':'Operability','crane_checklist':'CRANE INSPECTION',
        'remarks':'REMARKS BY CRANE',**{f'crane{i}':f'Crane {i}' for i in range(1,5)},
        'recommendations':'RECOMMENDATIONS','grabs_condition':'GRABS CONDITION SURVEY',
        'conclusion':'CONCLUSION','enclosure':'ENCLOSURE'}
GROUPS={'instructions':('crane_intro',),'gear':('gear_condition','gear_wires','gear_sheaves','gear_operability'),
        'crane_checklist':(),'remarks':tuple(f'crane{i}' for i in range(1,5)),
        'recommendations':(),'grabs_condition':(),'conclusion':(),'enclosure':()}
FIELDS={'imo':'IMO','length_and_tonnage':'Length overall and tonnage','grt':'GRT','nrt':'NRT',
        'cargo':'Cargo','inspection_date':'Inspection date','inspection_time':'Inspection time','period_start':'Survey start','period_end':'Survey end',
        'issue_date':'Date of issue','report_status':'Report status','surveyor':'Surveyor / signatory'}
LIMITS={key:(20 if key=='conclusion' else 1 if key in ('enclosure','crane_intro','gear_condition','gear_wires','gear_sheaves','gear_operability') else 10) for key in TITLES}
LIMITS['crane_checklist']=0


class CraneCheck(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    done: bool=False
    status: str=''
    status1: str=''
    status2: str=''
    status3: str=''

    @field_validator('status','status1','status2','status3')
    @classmethod
    def valid_status(cls,value):
        if value not in OPTIONS:raise ValueError('Unknown crane status')
        return value
