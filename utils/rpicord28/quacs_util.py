import time
import traceback
from datetime import datetime
from typing import Literal

import discord
import requests
from discord import app_commands
from discord.ext import commands
from pytz import timezone

from core import database
from core.rpi.course_data import CourseData
from core.rpi.quacs_base import Prerequisite, Restriction

# URLs to fetch the JSON files from GitHub
GITHUB_BASE_URL = 'https://raw.githubusercontent.com/quacs/quacs-data/master/semester_data/202409/'

FILE_URLS = {
    'catalog': GITHUB_BASE_URL + 'catalog.json',
    'courses': GITHUB_BASE_URL + 'courses.json',
    'reg_dates': GITHUB_BASE_URL + 'registration_dates.json',
    'schools': GITHUB_BASE_URL + 'schools.json',
    'prereqs': GITHUB_BASE_URL + 'prerequisites.json'
}

def fetch_data(file_urls):
    data = {}
    for key, url in file_urls.items():
        response = requests.get(url)
        if response.status_code == 200:
            data[key] = response.json()
        else:
            print(f"Failed to fetch {key}: {response.status_code}")
    return data

def parse_prereqs(prereqs):
    def recurse(nested):
        if isinstance(nested, list):
            return ' and '.join(recurse(item) for item in nested)
        elif isinstance(nested, dict):
            if 'nested' in nested:
                if nested['type'] == 'and':
                    return ' and '.join(recurse(item) for item in nested['nested'])
                elif nested['type'] == 'or':
                    return ' or '.join(recurse(item) for item in nested['nested'])
            else:
                course = nested.get('course', 'Unknown Course')
                grade = nested.get('min_grade', 'Unknown Grade')
                return f"{course} (min grade: {grade})"
        elif isinstance(nested, Prerequisite):
            if isinstance(nested.course, list):
                nested_str = ' and '.join(str(item) for item in nested.course) if nested.type == 'and' else ' or '.join(str(item) for item in nested.course)
                return f"({nested_str})"
            else:
                return str(nested)
        elif isinstance(nested, tuple) and isinstance(nested[0], Prerequisite) and isinstance(nested[1], Restriction):
            prereq_str = str(nested[0])
            restriction_str = str(nested[1])
            return f"{prereq_str}\n\n**Restrictions:** {restriction_str}"
        else:
            return "Unknown prerequisite format"
    return recurse(prereqs)


class RegistrationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.course_data = CourseData()

    QC = app_commands.Group(
        name="quacs",
        description="Commands for QuACS information.",
        guild_ids=[1216429016760717322, 1161339749487870062]
    )

    CR = app_commands.Group(
        name="schedule",
        description="Commands for scheduling.",
        guild_ids=[1216429016760717322, 1161339749487870062]
    )

    def split_into_chunks(self, sections, chunk_size):
        for i in range(0, len(sections), chunk_size):
            yield sections[i:i + chunk_size]

    @QC.command(name="registration_slots", description="Know when you can register for classes")
    async def reg_status(self, interaction: discord.Interaction, specific_timeslot: Literal["8:00 AM", "8:30 AM", "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM"] = None):
        """make a message containing all of the timeslots in relative timestamps with the discord feature. note all times are in est"""
        est = timezone('US/Eastern')

        today = datetime.now(est).date()
        timeslots = {
            "8:00 AM": est.localize(datetime.combine(today, datetime.strptime("08:00", "%H:%M").time())),
            "8:30 AM": est.localize(datetime.combine(today, datetime.strptime("08:30", "%H:%M").time())),
            "9:00 AM": est.localize(datetime.combine(today, datetime.strptime("09:00", "%H:%M").time())),
            "9:30 AM": est.localize(datetime.combine(today, datetime.strptime("09:30", "%H:%M").time())),
            "10:00 AM": est.localize(datetime.combine(today, datetime.strptime("10:00", "%H:%M").time())),
            "10:30 AM": est.localize(datetime.combine(today, datetime.strptime("10:30", "%H:%M").time())),
            "11:00 AM": est.localize(datetime.combine(today, datetime.strptime("11:00", "%H:%M").time())),
            "11:30 AM": est.localize(datetime.combine(today, datetime.strptime("11:30", "%H:%M").time())),
            "12:00 PM": est.localize(datetime.combine(today, datetime.strptime("12:00", "%H:%M").time())),
        }

        if specific_timeslot:
            if specific_timeslot in timeslots:
                timestamp = discord.utils.format_dt(timeslots[specific_timeslot], style='R')
                await interaction.response.send_message(f"Registration slot for {specific_timeslot} is {timestamp}.",
                                                        ephemeral=False)
            else:
                await interaction.response.send_message("Invalid timeslot specified.", ephemeral=False)
        else:
            message = "# Registration slots:\n"
            for time, dt in timeslots.items():
                timestamp = discord.utils.format_dt(dt, style='R')
                message += f"**{time}**: {timestamp}\n"
            await interaction.response.send_message(message, ephemeral=False)



    @QC.command(name='class_info', description='Get information about a class')
    @app_commands.describe(course_num='The course code, e.g., CSCI-1100')
    async def class_info(self, interaction: discord.Interaction, course_key: str, course_num: int, section_num: int = None, info_view: Literal["Basic", "Sections"]= "Basic"):
        await interaction.response.defer(thinking=True)
        course_data = self.course_data.get_course(course_key, course_num)
        if course_data == None:
            return await interaction.followup.send("No Course Found")
        catalog_data = self.course_data.get_course_catalog(course_key, course_num)

        if section_num:
            section = next((sec for sec in course_data.sections if sec.sec == str(section_num).zfill(2)), None)
            if section:
                timeslots = "\n".join(str(timeslot) for timeslot in section.timeslots)
                embed = discord.Embed(title=f"{course_key} {course_num} | {course_data.title}",
                                      description=catalog_data.description, color=0xde1f1f)
                embed.add_field(name=f"Section {section.sec}: {section.title} ({section.crn})",
                                value=f"Seats: {section.rem}/{section.cap}\nCredits: {section.cred_min}")
                embed.add_field(name="Time Met", value=f"{timeslots}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Section not found.")
        elif info_view == "Basic":
            embed = discord.Embed(title=f"{course_key} {course_num} | {course_data.title}",
                                  description=catalog_data.description, color=0xde1f1f)
            if course_data.sections[0].cred_min == course_data.sections[0].cred_max:
                credits = course_data.sections[0].cred_min
            else:
                credits = f"{course_data.sections[0].cred_min} - {course_data.sections[0].cred_max}"

            class_free = False
            for section in course_data.sections:
                if section.rem > 0:
                    class_free = True

            prereqs_raw = self.course_data.get_prereqs(course_data.sections[0].crn)
            prereqs = parse_prereqs(prereqs_raw) if prereqs_raw else "None"

            embed.add_field(name="Basic Information",
                            value=f"**Credits:** {credits}\n**Total Sections:** {len(course_data.sections)} sections.\n**Spots Available?:** {class_free}")
            embed.add_field(name="Prerequisites", value=f"{prereqs}")
            await interaction.followup.send(embed=embed)
        else:
            try:
                sections = course_data.sections
                chunks = list(self.split_into_chunks(sections, 25))
                for i, chunk in enumerate(chunks):
                    embed = discord.Embed(title=f"{course_key} {course_num} | {course_data.title}",
                                          description=catalog_data.description if i == 0 else None,
                                          color=0xde1f1f)
                    for section in chunk:
                        timeslots = "\n".join(str(timeslot) for timeslot in section.timeslots)
                        embed.add_field(name=f"Section {section.sec} ({section.crn}): {section.rem}/{section.cap}",
                                        value=f"{str(timeslots)}")
                    await interaction.followup.send(embed=embed)
            except Exception as e:
                print(e)

    @QC.command(name="crn_lookup", description="Get a class by a CRN")
    @app_commands.describe(crn="The CRN of the class")
    async def get_by_crn(self, interaction: discord.Interaction, crn: int):
        course_data, section_data = self.course_data.get_course_by_crn(crn)
        if not course_data:
            await interaction.response.send_message("Invalid CRN")
            return

        course_key, course_num = course_data.id.split("-")
        catalog_data = self.course_data.get_course_catalog(course_key, course_num)

        prereqs, restrictions = self.course_data.get_prereqs(crn)
        prereqs_str = parse_prereqs(prereqs) if prereqs else "None"
        restrictions_str = str(restrictions) if restrictions else "None"

        embed = discord.Embed(
            title=f"{course_data.id} ({course_data.title}) Section {section_data.sec} ({crn})",
            description=catalog_data.description,
            color=0xde1f1f
        )

        if section_data.cred_min == section_data.cred_max:
            credits = section_data.cred_min
        else:
            credits = f"{section_data.cred_min} - {section_data.cred_max}"

        embed.add_field(
            name="Basic Information",
            value=f"**Credits:** {credits}\n**Seats:** {section_data.rem}/{section_data.cap}"
        )
        embed.add_field(
            name="Prerequisites",
            value=prereqs_str
        )
        embed.add_field(
            name="Restrictions",
            value=restrictions_str
        )

        await interaction.response.send_message(embed=embed)


    @QC.command(name='reg_dates', description='Get registration dates')
    async def reg_dates(self, interaction: discord.Interaction):
        try:
            open_date, close_date = self.course_data.get_registration_dates()
            s_date_obj = datetime.strptime(open_date, '%Y-%m-%d')
            e_date_obj = datetime.strptime(close_date, '%Y-%m-%d')
            s_unix_timestamp = int(time.mktime(s_date_obj.timetuple()))
            e_unix_timestamp = int(time.mktime(e_date_obj.timetuple()))
            s_discord_timestamp = f"<t:{s_unix_timestamp}:R>"
            e_discord_timestamp = f"<t:{e_unix_timestamp}:R>"

            await interaction.response.send_message(f"**Registration Dates:**\nOpens: {open_date} | {s_discord_timestamp}\nCloses: {close_date} | {e_discord_timestamp}")
        except Exception as e:
            tb = e.__traceback__
            etype = type(e)
            exception = traceback.format_exception(etype, e, tb, chain=True)
            exception_msg = ""
            for line in exception:
                print(line)

    @QC.command(name='departments', description='List all departments and their codes')
    async def departments(self, interaction: discord.Interaction):
        try:
            dept_message = "**Departments and Codes:**\n"
            school_data = self.course_data.get_schools()
            for school in school_data:
                dept_message += f"\n**{school['name']}**\n"
                for dept in school['depts']:
                    dept_message += f"{dept['code']}: {dept['name']}\n"
            await interaction.response.send_message(dept_message)
        except Exception as e:
            tb = e.__traceback__
            etype = type(e)
            exception = traceback.format_exception(etype, e, tb, chain=True)
            exception_msg = ""
            for line in exception:
                print(line)

    @CR.command(name='add', description='Add a class to your schedule')
    @app_commands.describe(crn="The CRN of the class to add. (NOT IN THE FORMAT OF CSCI-1100 and etc)")
    async def add(self, interaction: discord.Interaction, crn: int):
        try:
            course_data, section_data = self.course_data.get_course_by_crn(crn)
            if course_data is not None:
                database.db.connect(reuse_if_open=True)
                q: database.ClassSchedule = database.ClassSchedule.create(
                    discord_id=interaction.user.id, crn=crn
                )
                q.save()
                database.db.close()

                await interaction.response.send_message(f"Added {course_data.id} ({course_data.title}) Section {section_data.sec} to your schedule!", ephemeral=True)
            else:
                await interaction.response.send_message("Invalid CRN", ephemeral=True)
        except Exception as e:
            tb = e.__traceback__
            etype = type(e)
            exception = traceback.format_exception(etype, e, tb, chain=True)
            exception_msg = ""
            for line in exception:
                print(line)

    @CR.command(name='remove', description='Remove a class from your schedule')
    @app_commands.describe(crn="The CRN of the class to remove. (NOT IN THE FORMAT OF CSCI-1100 and etc)")
    async def remove(self, interaction: discord.Interaction, crn: int):
        database.db.connect(reuse_if_open=True)
        query = database.ClassSchedule.select().where(
            database.ClassSchedule.discord_id == interaction.user.id,
            database.ClassSchedule.crn == crn
        )
        if query.exists():
            query = query.get()
            query.delete_instance()

            course_data, section_data = self.course_data.get_course_by_crn(crn)
            if course_data is not None:
                await interaction.response.send_message(f"Removed {course_data.id} ({course_data.title}) Section {section_data.sec} from your schedule!", ephemeral=True)
            else:
                await interaction.response.send_message(f"Removed {crn} from your schedule!", ephemeral=True)
        else:
            await interaction.response.send_message("CRN not found in your schedule!", ephemeral=True)
        database.db.close()

    @CR.command(name='list', description='List all classes you have added to your schedule')
    @app_commands.describe(quick_paste="Whether to just comma separate the CRN's to easily copy them.")
    async def list(self, interaction: discord.Interaction, quick_paste: bool = False):
        try:
            if quick_paste:
                database.db.connect(reuse_if_open=True)
                query = database.ClassSchedule.select().where(
                    database.ClassSchedule.discord_id == interaction.user.id
                )
                if query.exists():
                    crns = [row.crn for row in query]
                    await interaction.response.send_message("\n".join(str(crn) for crn in crns), ephemeral=True)
                else:
                    await interaction.response.send_message("No classes found in your schedule!", ephemeral=True)
                database.db.close()
            else:
                database.db.connect(reuse_if_open=True)
                query = database.ClassSchedule.select().where(
                    database.ClassSchedule.discord_id == interaction.user.id
                )
                if query.exists():
                    classes = []
                    for row in query:
                        course_data, section_data = self.course_data.get_course_by_crn(row.crn)
                        if course_data is not None:
                            classes.append(f"**{course_data.id}** ({course_data.title}) Section `{section_data.sec}`: {row.crn}")
                        else:
                            classes.append(str(row.crn))
                    await interaction.response.send_message("\n".join(classes), ephemeral=True)
                else:
                    await interaction.response.send_message("No classes found in your schedule!", ephemeral=True)
                database.db.close()
        except Exception as e:
            tb = e.__traceback__
            etype = type(e)
            exception = traceback.format_exception(etype, e, tb, chain=True)
            exception_msg = ""
            for line in exception:
                print(line)

    @CR.command(name='clear', description='Clear all classes from your schedule')
    async def clear(self, interaction: discord.Interaction):
        database.db.connect(reuse_if_open=True)
        query = database.ClassSchedule.select().where(
            database.ClassSchedule.discord_id == interaction.user.id
        )
        if query.count() > 0:
            for row in query:
                row.delete_instance()
            await interaction.response.send_message("Cleared all classes from your schedule!", ephemeral=True)
        else:
            await interaction.response.send_message("No classes found in your schedule!", ephemeral=True)

    @CR.command(name='compare', description='Compare your classes with a friend!')
    @app_commands.describe(user="The user to compare classes with")
    async def compare(self, interaction: discord.Interaction, user: discord.Member):
        database.db.connect(reuse_if_open=True)
        query = database.ClassSchedule.select().where(
            database.ClassSchedule.discord_id == interaction.user.id
        )
        query2 = database.ClassSchedule.select().where(
            database.ClassSchedule.discord_id == user.id
        )
        if query.exists() and query2.exists():
            crns = [row.crn for row in query]
            crns2 = [row.crn for row in query2]
            common = set(crns).intersection(crns2)
            if common:
                classes = []
                for crn in common:
                    course_data, section_data = self.course_data.get_course_by_crn(crn)
                    if course_data is not None:
                        classes.append(f"**{course_data.id}** ({course_data.title}) Section `{section_data.sec}`: {crn}")
                    else:
                        classes.append(str(crn))
                await interaction.response.send_message(f"Common classes with {user.mention}:\n\n" + "\n".join(classes), ephemeral=True)
            else:
                await interaction.response.send_message(f"No common classes found with {user.mention}!", ephemeral=True)
        else:
            await interaction.response.send_message("No classes found in your/their schedule!", ephemeral=True)
        database.db.close()

    @QC.command(name='help', description='Get information about available commands')
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Help - Available Commands", description="List of available commands",
                              color=0x00ff00)
        embed.add_field(name="/class_info",
                        value="Get information about a class.\nUsage: /class_info course_key=<course_key> course_num=<course_num> [section_num=<section_num>] [info_view=<info_view>]",
                        inline=False)
        embed.add_field(name="/crn_lookup", value="Get a class by a CRN.\nUsage: /crn_lookup crn=<crn>", inline=False)
        embed.add_field(name="/reg_dates", value="Get registration dates.\nUsage: /reg_dates", inline=False)
        embed.add_field(name="/departments", value="List all departments and their codes.\nUsage: /departments",
                        inline=False)
        embed.add_field(name="/add", value="Add a class to your schedule.\nUsage: /add crn=<crn>", inline=False)
        embed.add_field(name="/remove", value="Remove a class from your schedule.\nUsage: /remove crn=<crn>",
                        inline=False)
        embed.add_field(name="/list",
                        value="List all classes you have added to your schedule.\nUsage: /list [quick_paste=<True/False>]",
                        inline=False)
        embed.add_field(name="/clear", value="Clear all classes from your schedule.\nUsage: /clear", inline=False)
        embed.add_field(name="/compare", value="Compare your classes with a friend.\nUsage: /compare user=<user>",
                        inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(RegistrationCog(bot))