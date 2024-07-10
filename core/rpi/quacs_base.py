import requests
import json

class TimeSlot:
    def __init__(self, dateEnd, dateStart, days, instructor, location, timeEnd, timeStart):
        self.date_end = dateEnd
        self.date_start = dateStart
        self.days = days
        self.instructor = instructor
        self.location = location
        self.time_end = timeEnd
        self.time_start = timeStart

    def __str__(self):
        days_str = "/".join(self.days)
        time_start_str = self.convert_to_12hr_format(self.time_start)
        time_end_str = self.convert_to_12hr_format(self.time_end)
        return f"**{days_str}** on **{time_start_str}**-**{time_end_str}** by {self.instructor}"

    def convert_to_12hr_format(self, time):
        hours = time // 100
        minutes = time % 100
        period = "AM" if hours < 12 else "PM"
        hours = hours % 12
        hours = 12 if hours == 0 else hours
        return f"{hours}:{minutes:02} {period}"

class Section:
    def __init__(self, act, attribute, cap, credMax, credMin, crn, crse, rem, sec, subj, timeslots, title, xl_rem=None):
        self.act = act
        self.attribute = attribute
        self.cap = cap
        self.cred_max = credMax
        self.cred_min = credMin
        self.crn = crn
        self.crse = crse
        self.rem = rem
        self.sec = sec
        self.subj = subj
        self.timeslots = [TimeSlot(**timeslot) for timeslot in timeslots]
        self.title = title
        self.xl_rem = xl_rem

    def __str__(self):
        timeslot_info = "\n".join(str(timeslot) for timeslot in self.timeslots)
        if self.cred_max == self.cred_min:
            return f"Section {self.sec}: {self.title}\nSeats Free: {self.rem}/{self.cap}\nCredits: {self.cred_min}\nTimes:\n{timeslot_info}"
        else:
            return f"Section {self.sec}: {self.title}\nSeats Free: {self.rem}/{self.cap}\nCredits: {self.cred_min}-{self.cred_max}\nTimes:\n{timeslot_info}"

class Course:
    def __init__(self, crse, id, sections, subj, title):
        self.crse = crse
        self.id = id
        self.sections = [Section(**section) for section in sections]
        self.subj = subj
        self.title = title

    def __str__(self):
        section_info = "\n\n".join(str(section) for section in self.sections)
        return f"{self.crse}: {self.title}\nSections:\n{section_info}"

class CourseCatalog:
    def __init__(self, subj, crse, name, description, source):
        self.subj = subj
        self.crse = crse
        self.name = name
        self.description = description
        self.source = source

    def __str__(self):
        return f"{self.subj}-{self.crse}: {self.name}\n{self.description}\nSource: {self.source}"

class Prerequisite:
    def __init__(self, course, min_grade, type):
        self.course = course
        self.min_grade = min_grade
        self.type = type

    def __str__(self):
        return f"Prerequisite: {self.course} with a minimum grade of {self.min_grade}"


class Restriction:
    def __init__(self, major=None, classification=None):
        self.major = major or {}
        self.classification = classification or {}

    def __str__(self):
        restriction_strs = []
        if self.major:
            must_be_str = ', '.join(self.major.get('must_be', []))
            restriction_strs.append(f"Must be majoring in: {must_be_str}")
        if self.classification:
            must_be_str = ', '.join(self.classification.get('must_be', []))
            restriction_strs.append(f"Must be classified as: {must_be_str}")
        return "; ".join(restriction_strs) if restriction_strs else "No restrictions"