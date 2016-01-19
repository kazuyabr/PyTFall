init -9 python:
    #################################################################
    # CORE BUILDING CLASSES
    # BaseBuilding = Base class, needed if no other.
    # FamousBuilding = Adds fame and reputation mechanics to the building.
    # DirtyBuilding = Adds dirt and cleaning to the building.
    # UpgradableBuilding = Adds upgrades and adverts to the building.
    #
    # Examples:
    # class CityJail(Building): <-- Just a building
    # class TraningDungeon(UpgradableBuilding): <-- A Building that can be upgraded.
    # class Brothel(UpgradableBuilding, DirtyBuilding, FamousBuilding): <-- A building will upgrade, dirt and fame mechanics.
    #
    """Core order for SimPy jobs loop:2
    ***Needs update after restructuring/renaming.
    
    BUILDING:
        # Holds Businesses and data/properties required for operation.
        run_nd():
            # Setups and starts the simulation.
            *Generates Clients if required.
            *Builds workers list.
            *Logs the init data to the building.
            *Runs pre_day for all updates.
            *Creates SimPy Envoronment and runs it (run_jobs being the main controlling process)
            *Runs the post_nd.
            
        run_jobs():
            # Main controller for all businesses.
            *Builds a list of all workable business.
            *Adds run_job for all public_service businesses to Env
            *Adds a steady/conditioned stream of clients to the appropriate businesses and manages their stream:
                TODO: Management of clients in case of lack of the capacity needs to be added there and to child checkups:
                *Personal Service:
                    - Finds best client match using update.get_workers()
                    - Runs the job using: self.env.process(upgrade.request(client, char)) TODO: Rename appropriately.
                *Public Service:
                    - Simply sends client to business.
                    - Sends in Workers to serve/entertain the clients.
                    
                *Kicks clients if nothing could be arranged for them.
                    
    BUSINESS: (aka Upgrade)
        # Hold all data/methods required for business to operate.
        TODO: all_occs should return a constant instead of creating a set every time they are called.
        TODO: Businesses or Building should control clients that wish to remain for moar action.
        *workers = On duty characters.
        *habitabe/workable = selfexplanotory.
        *clients = clients used locally (maybe useful only for the public service?)
        *capacity = cap of the building such as amount of rooms/workspace.
        *jobs = only for businesses
        *get_workers:
            - Checks if a char is capable.
            - Checks if a char is willing.
            - Can also try to match find the best client for the job.
        
        SimPy Stuff:
            *res = Resource
            *time = cycle TODO: Prolly should be controled by the manager
            *is_running = May be useless
        
        *Personal Service:
            *find_best_match = finds a best client/worker combination.
            *request_room:
                - requests a room for worker/client.
                - adds a run_job process to Env
                - logs it all to main log
            *run_job:
                TODO: This may not be required together with request...
                - Waits for self.time delay
                - Calls the job so it can form an NDEvent
                - Manages workers
        
        *Public Service:
            TODO: Concider that run_job/use_worker may not overlap in times which can cause lack of earnings/tips.
            *active_workers = Does this not simply double the normal workers? TODO: Find out.
            *request = plainly adds a client and keeps it in the business based on "ready_to_leave" flag set directly to the client.
            *worker_control:
                # Adds workers to business to serve clients.
                - Checks willingness to do the job.
                - Adds workers as required.
                - self.env.process(self.use_worker(worker)) Possible the most important part, this adds a process to Env.
                - Removes from general instance workers list in order to reserve the worker for this business
            *run_job:
                # main method/SimPy event that manages the job from start to end.
                - Runs for as long there are active workers
                - Waits for self.time delay
                - Manages clients in the business
                - Calculates amount of earnings! Tips are being calced in use_worker!
                TODO: Seems that atm this just calcs the earning and waits for delays, it should be restructured appropriately and possibly merged with other methods.
            *use_worker:
                # Env Process, manages each individual worker.
                - Runs while there are clients and worker has AP in self.time delays.
                - Logs all active clients as flags to a worker.
                - Logs tips to the worker.
                - Runs the Job once AP had been exhausted or there are no more clients availible.
                - Removes the worker from active workers # TODO: Might be a good idea to move the worker back to self.instance_workers in case update simply ran out of clients.
    
    NewStyleJob:
        # Classes that hold funcitons and some default data.
        # We keep one instance of a job for the whole game whenever possible.
        *workermod = Any Stats/Skills changed during this Jobs execution
        *locmod = Same for the Building
        *occupations = Base occs like SIW/Server
        *occupation_traits = Direct Traits of chars that would be willing to do this job (currently we just use basetraits)
        
        *__call__ = Executes the job to do whatever it is supposed to.
        *reset = Resets the base properties for the job
        *all_occs = set(self.occupations + self.occupation_traits) # TODO: Should be a contant, no point in rebuilding the set every time.
        *get_clients = Returns the amount of clients required to properly run this job, not used afaik
        *create_event = Creates an event for the next day that will hold all the data required to display in reports.
        **check_occupation = ***Very important one, checks if the worker if willing to do the job.
        *check_life = Not used atm. TODO: Confirm and remove!
        **apply_stats = Applies Stats and Skills and Building mods accordingly.
        *loggs/logloc = Cool way to log the required stats to worker/building in order to have them applied later.
        **finish_job = Another really important one, this:
            - Creates the NDEvent
            - Resets the Job
    """
    
    class BaseBuilding(Location, Flags):
        """The super class for all Building logic.
        """
        def __init__(self, id=None, name=None, desc=None, price=1, minrooms=0, maxrooms=1, roomprice=250, mod=1, **kwargs):
            """
            Creates a new building.
            id = The id of the building.
            name = The name of the building.
            desc = The description of the building.
            price = The price of the building.
            minrooms = The minimum amount of rooms the building can have.
            maxrooms = The maximum amount of rooms the building can have.
            roomprice = The amount each room costs.
            mod = The modifier for the building.
            **kwargs = Excess arguments.
            """
            super(BaseBuilding, self).__init__()
            self.id = id
            self.name = name
            self.desc = desc
            self.price = price
            self.jobs = set()
            self.building_jobs = set()
            
            # Flagging
            self.flag_red = False
            self.flag_green = False
            self.highlighted = False
            
            # Rooms
            self.rooms = minrooms
            self.minrooms = minrooms
            self.maxrooms = maxrooms
            self.roomprice = roomprice
            self.mod = mod
            
            # Security
            self.security_rating = 0
            self.security_presence = 0
            
            # ND Report
            self.txt = ""
        
        def free_rooms(self):
            """
            The amount of rooms that aren't being used.
            """
            return self.rooms - len(self.get_girls())
        
        def get_girls(self, action=undefined, occupation=undefined, nott=False):
            """
            The girls that are in this location.
            action = The type of action the girls are doing.
            occupation = The occupation of the girls.
            nott = Whether to negate the selection.
            
            Note: undefined is used as an alternative to None, as a girl can have no action.
            """
            # Get all girls
            if action is undefined:
                g = [girl for girl in hero.girls if girl.location is self]
            
            # Only get girls that (don't) match action list
            elif isinstance(action, (list,tuple)):
                g = [girl for girl in hero.girls if girl.location is self and (girl.action in action) != nott]
            
            # Only get girls that are training
            elif action == "Course":
                g = [girl for girl in hero.girls if girl.location is self and girl.action is not None and girl.action.endswith("Course") != nott]
            
            # Only get girls with specific action
            else:
                g = [girl for girl in hero.girls if girl.location is self and (girl.action == action) != nott]
            
            # Get all girls
            if occupation is undefined:
                return g
            
            # Only get girls that (don't) match occupation list
            # TODO: NOT SURE IF THIS IS CORRECT AFTER THE REVIEW!
            elif isinstance(occupation, (list,tuple)):
                return [girl for girl in g if [tr for tr in girl.occupations if tr in occupation] != nott]
            
            # Only get girls with specific occupation
            else:
                return [girl for girl in g if (occupation in girl.occupations) != nott]
        
        def modrooms(self, value):
            """
            Modifies the amount of rooms the dungeon has.
            value = The amount to modify by.
            """
            if value > 0:
                if self.rooms + value > self.maxrooms: self.rooms = self.maxrooms
                else: self.rooms += value
            
            elif self.rooms + value < self.minrooms: self.rooms = self.minrooms
            else: self.rooms -= value
        
        def security_mult(self):
            """
            Get the multiplier caused by security presence.
            """
            return float(self.security_rating) / 1000.0
        
    
    class FamousBuilding(BaseBuilding):
        """
        A Building that has Fame and Reputation properties.
        """
        
        def __init__(self, *args, **kwargs):
            """
            Creates a new FamousBuilding.
            minfame = The minimum amount of fame the building can have.
            maxfame = The maximum amount of fame the building can have.
            minrep = The minimum amount of reputation the building can have.
            maxrep = The maximum amount of reputation the building can have.
            """
            super(FamousBuilding, self).__init__(*args, **kwargs)
            
            self.minfame = kwargs.pop("minfame", 0)
            self.maxfame = kwargs.pop("maxfame", 0)
            self.fame = self.minfame
            
            self.minrep = kwargs.pop("minrep", 0)
            self.maxrep = kwargs.pop("maxrep", 0)
            self.rep = self.minrep
        
        def modfame(self, value):
            """
            Changes how famous this building is.
            value = The amount to change.
            """
            if self.fame+value > self.maxfame:
                self.fame = self.maxfame
                return
            
            if value < 0:
                if self.fame+value < self.minfame:
                    self.fame = self.minfame
                    return
            
            self.fame += value
        
        def modrep(self, value):
            """
            Changes how reputable this building is.
            value = The amount to change.
            """
            if self.rep+value > self.maxrep:
                self.rep = self.maxrep
                return
            
            if value < 0:
                if self.rep+value < self.minrep:
                    self.rep = self.minrep
                    return
            
            self.rep += value
        
    
    class DirtyBuilding(BaseBuilding):
        """
        A building that has Dirt and Cleaning mechanics.
        """
        
        DIRT_STATES = dict(Immaculate=(0, 10), Sterile=(10, 20), Spotless=(20, 30), Clean=(30, 40), Tidy=(40, 50), Messy=(50, 60), Dirty=(60, 70), Grimy=(70, 80), Filthy=(80, 90), Disgusting=(90, 100))
        
        def __init__(self, *args, **kwargs):
            """
            Creates a new DirtyBuilding.
            sq_meters = The m^2 that each room takes up.
            """
            super(DirtyBuilding, self).__init__(*args, **kwargs)
            
            self.dirt = 0
            self.auto_clean = False
            self.sq_meters = kwargs.pop("sq_meters", 0)
        
        def get_max_dirt(self):
            """
            The total amount of dirt this building can have.
            """
            rooms = float(self.rooms) / self.maxrooms
            return int(self.sq_meters*0.8*rooms)
        
        def get_dirt(self):
            """
            The amount of dirt this building has.
            """
            if self.dirt > self.get_max_dirt():
                return self.get_max_dirt()
            
            else:
                return self.dirt
        
        def get_cleaning_price(self):
            """
            How much it costs to clean this building.
            """
            dirt = self.get_dirt()
            price = 10 + dirt + dirt
            return int(round(price))
        
        def get_dirt_percentage(self):
            """
            Returns percentage of dirt in the building as (percent, description).
            """
            dirt = self.dirt * 100 / self.get_max_dirt()
            if dirt > 100:
                dirt = 100
            
            dirt_string = ""    
            for key in self.DIRT_STATES:
                if dirt >= self.DIRT_STATES[key][0] and dirt <= self.DIRT_STATES[key][1]:
                    dirt_string = key
            
            if not dirt_string:
                raise Exception, "No valid string for dirt percentage of %s was found!" % self.id
            
            return int(round(dirt)), dirt_string
        
        def clean(self, value):
            """
            Cleans the building of the given amount of dirt.
            value = The amount to clean.
            """ 
            if self.dirt > self.get_max_dirt():
                self.dirt = self.get_max_dirt()
            
            if self.dirt - value > 0:
                self.dirt -= value
            
            elif self.dirt - value <= 0:
                self.dirt = 0
        
    
    class UpgradableBuilding(BaseBuilding):
        """
        An extension to Buildings that allows them to be upgradable.
        """
        # The flag for an upgrade that increases the room price
        ROOM_UPGRADE = "room_upgrade"
        
        # The flag for an upgrade that increases the security rating
        SECURITY_UPGRADE = "security_bonus"
        
        # The flag for an upgrade that increases the whore cost.
        WHORE_MULTIPLIER = "whore_mult"
        
        def __init__(self, *args, **kwargs):
            """
            Creates the necessary data for building information.
            """
            super(UpgradableBuilding, self).__init__(*args, **kwargs)
            
            self.upgrade_slots = kwargs.pop("upgrade_slots", 0)
            self.upgrades = OrderedDict()
            self.used_upgrade_slots = 0
            
            self.adverts = OrderedDict()
            
            # Runaway Manager modifier for runaway chances.
            self.security_upgrade_tree = kwargs.pop("sutree", "Security")
        
        def get_room_price(self):
            """
            Get the price of a new room.
            """
            return self.roomprice * self.mod + self.get_upgrade_flag("room_upgrade")
        
        def get_upgrade_flag(self, name):
            """
            Gets the total of a specific flag for those upgrades that are active.
            name = The name of the flag.
            """
            f = 0
            for i in self.upgrades:
                i = self.upgrades[i]
                for j in i:
                    if name in i[j] and i[j]["active"]: f += i[j][name]
            
            return f
        
        def get_upgrade_mod(self, name):
            """
            Gets the modifier for the upgrades.
            name = The name of the group.
            """
            if name not in self.upgrades: return 0
            
            f = 0
            for i in xrange(1, len(self.upgrades[name])+1):
                if self.has_upgrade(name, i): f += 1
            
            return f
        
        def get_upgrade_price(self, dict):
            """
            Get the price to upgrade the location.
            dict = The upgrade to price.
            """
            if "room_dependant" in dict:
                return dict["price"] + dict["price"]/10*self.rooms
            
            else:
                return dict["price"] * self.mod
        
        def gui_security_bar(self):
            """
            Returns a tuple of (Show security bar, Max value).
            """
            return [len(self.get_girls("Guard")) > 0, 20 + self.get_upgrade_flag("security_bonus")]
        
        def has_upgrade(self, name, index):
            """
            Gets whether an upgrade is installed or not.
            name = The name of the group.
            index = The index or name of upgrade.
            """
            if name in self.upgrades:
                up = self.upgrades[name]
                if isinstance(index, int):
                    for i in up:
                        if up[i]["id"] == index:
                            return up[i]["active"]
                    else:
                        return False
                
                else:
                    if index in up:
                        return up[index]["active"]
                    else:
                        for i in up:
                            if up[i]["name"] == index:
                                return up[i]["active"]
                        else:
                            return False
            else:
                return False
        
        def init(self):
            """Activate any upgrades from plain properties in the instance, then remove them.
            
            Meant for json completion.
            """
            for key in self.upgrades:
                if hasattr(self, key):
                    amount = getattr(self, key)
                    
                    for ukey in self.upgrades[key]:
                        if self.upgrades[key][ukey]["id"] <= amount: self.upgrades[key][ukey]['available'] = True
                    
                    delattr(self, key)
        
        def use_adverts(self):
            """Whether this building has any adverts.
            """
            return len(self.adverts) > 0
        
        @property
        def use_upgrades(self):
            """Whether this building has any upgrades.
            """
            return len(self.upgrades) > 0
        
    class NewStyleUpgradableBuilding(BaseBuilding):
        def __init__(self, *args, **kwargs):
            """
            @ Last review:
            Alex: I've moved everything except adverts and methods from Building class here.
            """
            super(NewStyleUpgradableBuilding, self).__init__(*args, **kwargs)
            self._upgrades = list() #  New style Upgrades!
            
            # And new style upgrades:
            self.in_slots = 100 # Interior Slots
            self.ex_slots = 100 # Exterior Slots
            
            if hasattr(self, "building_jobs"): # BAD Code, right now all jobs are kept in .jobs attribute...
                self.building_jobs = self.building_jobs.union(self.building_jobs)
                
            # Clients:
            self.all_clients = set() # All clients of this building are maintained here.
            self.regular_clients = set() # Subset of self.all_clients.
            self.clients = set() # Local clients, this is used during next day and reset on when that ends.
            
            # Chars:
            self.manager = None
            self.workers = list() # All Workers...
            
            # Upgrades:
            self.nd_ups = list() # Upgrades active during the next day...
                
            # SimPy and etc follows (L33t stuff :) ):
            self.env = None
            self.maxrank = kwargs.pop("maxrank", 0) # @Useless property...
            
            self.logged_clients = False
            self.total_clients = 0 # This is the amount of clients that will visit the brothel, this is set by get_client_count method.
            self.mod = 1
            
            self.fin = Finances(self)
            
        def run_nd(self):
            tl.timer("Temp Jobs Loop")
            # Setup and start the simulation
            self.flag_red = False
            
            self.log(set_font_color("===================", "lawngreen"))
            self.log("{}".format(set_font_color("Starting the simulation:", "lawngreen")))
            self.log("--- Testing {} Building ---".format(set_font_color(self.name, "lawngreen")))
            
            # All workers and workable businesses:
            self.workers = list(c for c in hero.girls if c.location == self and c.action in self.jobs) # The last check may not be good enought, may need rewriting.
            self.nd_ups = list(up for up in self._upgrades if up.workable) # Get all businesses! #IMPORTANT! Businesses that do not take clients should be removed from here!
            
            # Clietns:
            tl.timer("Generating clients")
            self.get_client_count(write_to_nd=True)
            clnts = self.total_clients
            # TODO: Generate and add regulars!
            # ALSO: We at the moment randomly pick a business for a client to like, that may need to be adjusted.
            if self.nd_ups and self.workers:
                if len(self.all_clients) < clnts:
                    for i in xrange(clnts - len(self.all_clients)):
                        if dice(80):
                            self.all_clients.add(build_client(likes=[choice(self.nd_ups)]))
                        else:
                            self.all_clients.add(build_client(gender="female", likes=[choice(self.nd_ups)]))
            self.clients = self.all_clients.copy()
            self.log("Total of {} clients are expected to visit this establishment!".format(set_font_color(len(self.clients), "lawngreen")))
            tl.timer("Generating clients")
            
            # Create an environment and start the setup process:
            self.env = simpy.Environment()
            for up in self._upgrades:
                up.pre_nd()
                
            self.env.process(self.clients_dispatcher(end=100))
            self.env.run(until=100)
            self.log("{}".format(set_font_color("Ending the simulation:", "red")))
            # self.env.run(until=110)
            # self.log("{}".format(set_font_color("Ending the second stage of simulation:", "red")))
            
            self.log("\nA total of {} Gold was earned here today!".format(set_font_color(str(self.fin.get_work_income()), "red")))
            self.log("{}".format(set_font_color("===================", "red")))
            self.log("\n\n")
            tl.timer("Temp Jobs Loop")
            
            self.post_nd_reset()
            
        def get_client_count(self, write_to_nd=False):
            """Get the amount of clients that will visit the brothel the next day.
            """
            
            if not self.fame and not self.rep and not self.adverts['sign']['active']:
                if write_to_nd:
                    self.log("{}".format(set_font_color("Noone came to your unknown establishment that doesn't have as much as a sign!", "red")))
                    self.flag_red = True
                return 0
            
            clients = self.baseclients*int(round(self.mod*1.5))
            if write_to_nd:
                self.log("{} clients came to brothel just because its there!".format(set_font_color(clients, "green")))
            
            if config.debug:
                debug_add = 10
                if write_to_nd:
                    self.log("Debug Mode adding {} clients!".format(set_font_color(debug_add, "red")))
                clients = clients + debug_add
            
            # Generated by upgrades:
            for u in [u for u in self._upgrades if u.workable]:
                temp = u.get_client_count()
                if write_to_nd and config.debug:
                    self.log("Debug: {} upgrade is adding {} clients!".format(u.name, set_font_color(temp, "red")))
                clients = clients + temp
            
            add_clients = int(self.fame*0.2)
            if add_clients and write_to_nd:
                self.log("{} clients came due to {} renoun!".format(add_clients, self.name))
            clients = clients + add_clients
            
            self.total_clients = clients if clients > 0 else 0
            
        def log(self, item):
            # Logs the text to log...
            self.nd_events_report.append(item)
            if config.debug and True:
                devlog.info(item)
            
        def normalize_jobs(self):
            self.jobs = self.jobs.union(self.building_jobs)
            for up in self._upgrades:
                self.jobs = self.jobs.union(up.jobs)
                
        def can_add_upgrade(self, upgrade, build=False):
            # Check if building has enough space to add this upgrade
            if self.in_slots < upgrade.in_slots or self.ex_slots < self.ex_slots:
                return
                
            # Check is there is already this type of an upgrade:
            if list(up for up in self._upgrades if up.__class__ == upgrade.__class__):
                return
                
            # If we want to build the upgrade as well:
            if build:
                self.add_upgrade(upgrade)
                self.normalize_jobs()
                
            return True
                
        def add_upgrade(self, upgrade):
            """Add upgrade to the building.
            """
            upgrade.instance = self
            self._upgrades.append(upgrade)
            
        @property
        def habitable(self):
            """
            Returns True if this buildings has upgrades with free living space.
            """
            return any(i.habitable for i in self._upgrades)
            
        @property
        def workable(self):
            """Returns True if this building has upgrades that are businesses.
            """
            return any(i.workable for i in self._upgrades)
            
        # SimPy:
        def clients_dispatcher(self, end=40):
            """This method provides stream of clients to the building following it's own algorithm.
            """
            
            # TODO: Improve the function and add possibilities for "Rush hours"
            for u in self.nd_ups:
                # Trigger all public businesses:
                # if u.type == "public_service":
                self.env.process(u.business_control())
                
                if u.has_workers():
                    u.is_running = True
            
            # For Jobs that require clients to run:
            i = 0
            ii = 0
            if self.clients:
                iii = randint(3, len(self.clients)/20)
            else:
                iii = 0
                
            while self.clients and self.nd_ups and self.env.now <= end:
                if ii > iii:
                    delay = randint(1, 3)
                    yield self.env.timeout(delay)
                    # Ensure a steady stream if clients:
                    ii = 0
                    if len(self.clients) > end - self.env.now:
                        iii = (len(self.clients) / (end - self.env.now))
                i += 1
                ii += 1
                client = self.clients.pop()
                self.env.process(self.client_manager(client))
            
        def client_manager(self, client):
            """Manages a client using SimPy.
            
            - Picks a business
            - Tries other businesses if the original choice fails
            - Kicks the client if all fails
            
            So this basically sends the client into the businesses within this building or keeps them waiting/rotating.
            Once in, client is handled and managed by the Business itself until control is returned here!
            Once this method is terminated, client has completely left the building!
            """
            # Register the fact that client arrived at the building:
            temp = '{}: {} arrives at the {}.'.format(self.env.now, client.name, self.name)
            self.log(temp)
            
            # Visit counter:
            client.up_counter("visited_building" + self.id)
            
            # Prepear data:
            businesses = self.nd_ups[:]
            shuffle(businesses)
            
            # TODO: Add Matron/Client likes effects here and to client classes.
            fav_business = client.likes.intersection(self._upgrades)
                
            if not fav_business: # Case where clients fav business was removed from the building, we would the client to react appropriately.
                self.all_clients.remove(client)
                temp = "{}: {} leaves the building pissed off as his favorite business was removed!".format(self.env.now, client.name)
                self.log(temp)
                # We may be required to yield here due to SimPy structure!
                return
            else:
                fav_business = fav_business.pop()
            
            visited = 0 # Amount of businesses client has successfully visited.
            while businesses: # Manager effects should be a part of this loop as well!
                # Here we pick an upgrade if a client has one in preferences:
                if not visited and fav_business in businesses:
                    # On the first run we'd want to pick the clients fav.
                    upgrade = fav_business
                    businesses.remove(upgrade)
                else:
                    upgrade = businesses.pop()
                
                # Matron case:
                # Wait for the business to open in case of a favorite:
                if self.manager and upgrade == fav_business:
                    timer = 0
                    if upgrade.res.count < upgrade.capacity:
                        while timer < 7 and upgrade.res.count < upgrade.capacity: # Max wait time
                            timer = timer + 1
                            yield self.env.timeout(1)
                            
                if upgrade.type == "personal_service" and upgrade.res.count < upgrade.capacity:
                    # Personal Service (Brothel-like):
                    job = upgrade.job
                    workers = upgrade.get_workers(job, amount=1, match_to_client=client)
                    
                    if not workers:
                        continue # Send to the next update.
                    else:
                        # We presently work just with the one char only, so:
                        worker = workers.pop()
                        if worker in self.workers:
                            self.workers.remove(worker)
                            
                        # We bind the process to a flag and wait until it is interrupted:
                        visited += 1
                        # client.set_flag("jobs_busy", self.env.process(upgrade.request_room(client, worker)))
                        # raise Exception(client.flag("jobs_busy").__dict__)
                        # while self.env.process(upgrade.request_room(client, worker)).is_alive:
                            # yield self.env.timeout(1)
                        self.env.process(upgrade.request_room(client, worker))
                        client.set_flag("jobs_busy")
                        while client.flag("jobs_busy"):
                            yield self.env.timeout(1)
                        
                # Jobs like the Club:
                elif upgrade.type == "public_service" and upgrade.res.count < upgrade.capacity:
                    self.env.process(upgrade.client_control(client))
                    upgrade.worker_control()
                    visited += 1
                    client.set_flag("jobs_busy")
                    while client.flag("jobs_busy"):
                        yield self.env.timeout(1)
                    
            if not visited:
                temp = "{}: There is not much for the {} to do...".format(self.env.now, client.name)
                self.log(temp)
                temp = "{}: So {} leaves your establishment cursing...".format(self.env.now, client.name)
                self.log(temp)
                yield self.env.timeout(0) # To make sure this is a generator :)
            else:
                temp = '{}: {} is leaving after visiting {} businesses.'.format(self.env.now, client.name, visited)
                self.log(temp)
            
                    
        def post_nd_reset(self):
            self.env = None
            self.nd_ups = list()
            
            for _ in self._upgrades:
                _.post_nd_reset()
                
            for c in self.all_clients:
                for f in c.flags.keys():
                    if f.startswith("jobs"):
                        c.del_flag(f)
