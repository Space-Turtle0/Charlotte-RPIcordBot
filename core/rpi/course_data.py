import requests
from core.rpi.quacs_base import Course, Prerequisite, CourseCatalog, Section, Restriction


class CourseData:
    GITHUB_BASE_URL = 'https://raw.githubusercontent.com/quacs/quacs-data/master/semester_data/202409/'

    FILE_URLS = {
        'catalog': GITHUB_BASE_URL + 'catalog.json',
        'courses': GITHUB_BASE_URL + 'courses.json',
        'prereqs': GITHUB_BASE_URL + 'prerequisites.json',
        'registration_dates': GITHUB_BASE_URL + 'registration_dates.json',
        'schools': GITHUB_BASE_URL + 'schools.json'
    }

    def __init__(self):
        self.catalog_data = self.fetch_data(self.FILE_URLS['catalog'])
        self.courses_data = self.fetch_data(self.FILE_URLS['courses'])
        self.prereqs_data = self.fetch_data(self.FILE_URLS['prereqs'])
        self.registration_data = self.fetch_data(self.FILE_URLS['registration_dates'])
        self.school_data = self.fetch_data(self.FILE_URLS['schools'])

    def fetch_data(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch data from {url}: {response.status_code}")
            return None

    def get_course_catalog(self, course_key, course_num):
        """
        Get a course from the course catalog data.
        :param course_key: The course key (e.g., CSCI)
        :param course_num: The course number (e.g., 1100)

        :return: A CourseCatalog object if found, otherwise None
        """
        key = f"{course_key}-{course_num}"
        if key in self.catalog_data:
            return CourseCatalog(**self.catalog_data[key])
        return None

    def get_course(self, course_key, course_num):
        """
        Get a course from the course data.
        :param course_key: The course key (e.g., CSCI)
        :param course_num: The course number (e.g., 1100)

        :return: A Course object if found, otherwise None
        """
        for subject in self.courses_data:
            if subject['code'] == course_key:
                for course in subject['courses']:
                    if course['crse'] == course_num:
                        return Course(**course)
        return None

    def get_prereqs(self, crn):
        if str(crn) in self.prereqs_data:
            prereqs_data = self.prereqs_data[str(crn)].get('prerequisites')
            restrictions_data = self.prereqs_data[str(crn)].get('restrictions')

            prereqs = None
            if prereqs_data:
                if 'course' in prereqs_data:
                    prereqs = Prerequisite(
                        course=prereqs_data['course'],
                        min_grade=prereqs_data['min_grade'],
                        type=prereqs_data['type']
                    )
                elif 'nested' in prereqs_data:
                    nested_reqs = [Prerequisite(**req) for req in prereqs_data['nested']]
                    prereqs = Prerequisite(
                        course=nested_reqs,
                        min_grade=None,
                        type=prereqs_data['type']
                    )

            restrictions = None
            if restrictions_data:
                major = restrictions_data.get('major')
                classification = restrictions_data.get('classification')
                restrictions = Restriction(major=major, classification=classification)

            return prereqs, restrictions
        return None, None

    def get_prerequisites(self, course_key, course_num):
        course = self.get_course(course_key, course_num)
        if course:
            prereqs_list = []
            restrictions_list = []
            for section in course.sections:
                prereq, restriction = self.get_prereqs(section.crn)
                if prereq:
                    prereqs_list.append(str(prereq))
                if restriction:
                    restrictions_list.append(str(restriction))
            return prereqs_list, restrictions_list
        return None, None

    def get_registration_dates(self):
        open_date = self.registration_data['registration_opens']
        close_date = self.registration_data['registration_closes']
        return open_date, close_date

    def get_schools(self):
        return self.school_data

    def get_course_by_crn(self, crn):
        for subject in self.courses_data:
            for course in subject['courses']:
                for section in course['sections']:
                    if section['crn'] == crn:
                        course_obj = Course(**course)
                        section_obj = Section(**section)
                        return course_obj, section_obj
        return None, None