#!/usr/bin/python
# -*- coding: utf-8 -*-
#Importacion de librerias
import webapp2
import os
import jinja2
import logging
import datetime
import httplib2

from time import gmtime, strftime
from Crypto.Hash import SHA256
from google.appengine.ext import ndb
from webapp2_extras import sessions
from google.appengine.api import mail
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp.mail_handlers import BounceNotification
from google.appengine.ext.webapp.mail_handlers import BounceNotificationHandler
from apiclient.discovery import build
from oauth2client.appengine import OAuth2Decorator

mail_message = mail.EmailMessage()

class Correos(ndb.Model):
	message_body = ndb.StringProperty()

#Librería Jinja2
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

#************ oauth2Decorator
decorator = OAuth2Decorator(
	client_id='750516441288-39mbu5vjooc2iebqs6pue8jn0qf3dhf6.apps.googleusercontent.com',
	client_secret='pMF2haGpvXCFiJ9kdK9IyBLl',
	scope='https://www.googleapis.com/auth/tasks https://www.googleapis.com/auth/calendar')
service = build('tasks','v1')
service_calendar = build('calendar', 'v3')

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

class Handler(webapp2.RequestHandler):
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()

    def render(self, template, **kw):
		self.response.out.write(render_str(template, **kw))

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

#Describe las entidades del datastore
class Name(ndb.Model):
	Nom = ndb.StringProperty()
	ApellidoPaterno = ndb.StringProperty()
	ApellidoMaterno = ndb.StringProperty()
class Usuarios(ndb.Model):
	Clave = ndb.IntegerProperty()
	Nombre = ndb.StructuredProperty(Name, repeated=True)
	Contrasena = ndb.StringProperty()
	Fecha_Nacimiento = ndb.DateProperty()
	Sexo = ndb.BooleanProperty()
	Nacionalidad = ndb.StringProperty()
	Correo = ndb.StringProperty()
class Cuenta(ndb.Model):
	Usuario = ndb.StringProperty()
	Nombre = ndb.StringProperty()
	Saldo = ndb.FloatProperty()
class IngresoNDB(ndb.Model):
	Usuario = ndb.StringProperty()
	Categoria = ndb.StringProperty()
	Fecha = ndb.DateProperty()
	Ingreso = ndb.FloatProperty()
	Cuenta = ndb.StringProperty()
class EgresoNDB(ndb.Model):
	Usuario = ndb.StringProperty()
	Categoria = ndb.StringProperty()
	Fecha = ndb.DateProperty()
	Egreso = ndb.FloatProperty()
	Cuenta = ndb.StringProperty()
#Clase principal
#*****************************************************************Registro-Logueo-Contacto********************************************************
class Index(Handler):
    def get(self):
        self.render("index.html")
    def post(self):
        user = self.request.get('lg_username')
        pasw = self.request.get('lg_password')

        pw = SHA256.new(pasw).hexdigest()

        if pasw == '' or user == '':
            msg = 'Corrreo y password no especificados'
            self.render("index.html", error=msg)
        else:
            consulta=Usuarios.query(ndb.AND(Usuarios.Correo==user, Usuarios.Contrasena==pw)).get()
            if consulta is not None:
                logging.info('POST consulta=' + str(consulta))
        		#Vinculo el usuario obtenido de mi datastore con mi sesion.
                self.session['Correo'] = consulta.Correo
                mail = self.session.get('Correo')
                clave = self.session.get('Clave')
                if mail=="Admin":
                    self.render("_base2.html", correo=mail)
                else:
					self.redirect('/principal')
                    # self.render("_base.html", correo=mail)
            else:
                logging.info('POST consulta=' + str(consulta))
                msg = 'Usuario o password no coinciden'
                self.render("index.html", error=msg)

class Registro(Handler):
    #Metodo get
	def get(self):
		self.render("registro.html")
	def post(self):
		#Obtener valores del formulario
		email = self.request.get('reg_email')
		name = self.request.get('reg_name')
		ape = self.request.get('reg_ap')
		ape2 = self.request.get('reg_am')
		contra = self.request.get('reg_password')
		contra2 = self.request.get('reg_password_confirm')
		date = self.request.get('reg_date')
		nation = self.request.get('reg_nat')
		genero = self.request.get('reg_gender')
		if email == "" or name == "" or ape =="" or ape2 == "" or contra == "" or contra2 =="" or date == "" or nation == "" :
			err = "Debes llenar todos los campos"
			self.render("registro.html", error=err)
		else:
			# consulta=Usuarios.query(Usuarios.Correo==email).get()
			# if consulta == "":
			if contra==contra2:
				#API de correo (envio)
				message = mail.EmailMessage(sender="CEATyP Support <ceatyp@appspot.gserviceaccount.com>",
				                    subject="Your account has been approved")

				message.to = email
				message.body = """
				Dear """+name+""":

				Your example.com account has been approved.  You can now visit
				http://ceatyp.appspot.com/ and sign in using your Google Account to
				access new features.

				Please let us know if you have any questions.

				The CEATyP Team
				"""
				message.send()

				#Se crea ahora una entidad de tipo Usuarios y se escribe en el datastore.
				con = SHA256.new(contra).hexdigest()
				cuenta = Usuarios(Clave=0,
				Nombre=[Name(Nom=name,ApellidoPaterno=ape,ApellidoMaterno=ape2)],
				Contrasena=con, Fecha_Nacimiento=datetime.datetime.strptime(date, "%Y-%m-%d"), Sexo=str2bool(genero), Nacionalidad=nation, Correo=email)
				#El valor regresado por put es una llave, la cual puede ser usada para obtener nuevamente la misma entidad.
				cuentakey = cuenta.put()

				#Obtengo la entidad
				cuenta_user=cuentakey.get()
				if cuenta_user == cuenta:
					succ = "Gracias por registrarse..."
					self.render("registro.html", success=succ)
			else:
				err = "Password no coincide"
				self.render("registro.html", error=err)
			# else:
			# 	err = "El correo ya esta registrado"
			# 	self.render("registro.html", error=err)

class Logout(Handler):
    def get(self):
        if self.session.get('Correo'):
            #msg = 'You are loging out..'
            # self.render("index.html")
            self.redirect('/')
            del self.session['Correo']

class Contacto(Handler):
    #Metodo get
    def get(self):
        self.render("contacto.html")
    def post(self):
		#Capturo los datos de la vista
		global mail_message
		sender_email = self.request.get("email")
		logging.info("sender_email: " + sender_email)
		message = self.request.get("message")
		logging.info("message: " + message)

		#Defino el correo de la aplicacion, en donde se mandara el mensaje.
		app_mail = "ceatyp@appid.appspotmail.com"

		#Envio el correo a la aplicacion.
		mail_message.sender = sender_email
		mail_message.to = app_mail
		mail_message.subject = "Esto es una prueba"
		mail_message.body = message
		mail_message.send()

		#Muestro un mensaje de que su mensaje ha sido enviado

		self.response.write("Gracias, su mensaje se ha enviado.")

#************************************************************************Tareas**********************************************************************************
class Tarea(Handler):
    #Metodo get
	def get(self):
		mail = self.session.get('Correo')
		logging.info('Fecha: '+ str(mail))
		self.render("addtarea.html", correo=mail)
	@decorator.oauth_required
	def post(self):
		mail = self.session.get('Correo')
		titulo = self.request.get('titulo')
		nota = self.request.get('nota')
		fecha = self.request.get('fecha')
		if titulo == "" or nota == "" or fecha == "":
			err = "Completa todos los datos"
			self.render("addtarea.html", correo=mail, error=err)
		else:
			fecha = fecha+"T00:00:00.000Z"
			task = {
			  'title': titulo,
			  'notes': nota,
			  'due': fecha
			  }
			result = service.tasks().insert(tasklist='@default', body=task).execute(http=decorator.http())
			print result['id']
			logging.info('Fecha: '+ fecha)
			succ = "Tarea Agregada Corectamente"
			self.render("addtarea.html", correo=mail, success=succ)

class TareaDel(Handler):
	@decorator.oauth_required
	def get(self):
		idtask = self.request.get('idtask')
		mail = self.session.get('Correo')
		# self.response.write(idtask)
		service.tasks().delete(tasklist='@default', task=idtask).execute(http=decorator.http())
		self.redirect('/tareasv')

class TareaUpd(Handler):
	@decorator.oauth_required
	def get(self):
		idtask = self.request.get('idtask')
		mail = self.session.get('Correo')
		task = service.tasks().get(tasklist='@default', task=idtask).execute(http=decorator.http())
		self.render("updtarea.html", correo=mail, task=task)
	@decorator.oauth_required
	def post(self):
		idtask = self.request.get('idtask')
		mail = self.session.get('Correo')
		titulo = self.request.get('titulo')
		nota = self.request.get('nota')
		fecha = self.request.get('fecha')
		if titulo == "" or nota == "" or fecha == "":
			err = "Completa todos los datos"
			task = service.tasks().get(tasklist='@default', task=idtask).execute(http=decorator.http())
			self.render("updtarea.html", correo=mail, error=err, task=task)
		else:
			fecha = fecha+"T00:00:00.000Z"
			task = service.tasks().get(tasklist='@default', task=idtask).execute(http=decorator.http())
			task = {
			  "kind": "tasks#task",
			  "id": task['id'],
			  "etag": task['etag'],
			  "title": titulo,
			  "updated": task['updated'],
			  "selfLink": task['selfLink'],
			  "position": task['position'],
			  "notes": nota,
			  "status": task['status'],
			  "due": fecha
			}
			service.tasks().update(tasklist='@default', task=idtask, body=task).execute(http=decorator.http())
			self.redirect('/tareasv')
class TareaStatus(Handler):
	@decorator.oauth_required
	def get(self):
		idtask = self.request.get('idtask')
		mail = self.session.get('Correo')
		task = service.tasks().get(tasklist='@default', task=idtask).execute(http=decorator.http())
		task = {
		  "kind": "tasks#task",
		  "id": task['id'],
		  "etag": task['etag'],
		  "title": task['title'],
		  "updated": task['updated'],
		  "selfLink": task['selfLink'],
		  "position": task['position'],
		  "notes": task['notes'],
		  "status": "completed",
		  "due": task['due']
		}
		service.tasks().update(tasklist='@default', task=idtask, body=task).execute(http=decorator.http())
		self.redirect('/tareasv')

class TareaView(Handler):
	@decorator.oauth_required
    #Metodo get
	def get(self):
		# mail = self.session.get('Correo')
		# tasks=service.tasks().list(tasklist='@default').execute(http=decorator.http())
		# items = tasks.get('items', [])
		# response = '\n'.join([task.get('title','') for task in items])
		# self.render("viewtareas.html", correo=mail, response=items)
		mail = self.session.get('Correo')
		if decorator.has_credentials():
			result = service.tasks().list(tasklist='@default').execute(http=decorator.http())
			tasks = result.get('items', [])
			for task in tasks:
				task['title_short'] = truncate(task['title'], 26)
			self.render("viewtareas.html", correo=mail, tasks=tasks)
		else:
			url = decorator.authorize_url()
			self.render("viewtareas.html", correo=mail, tasks=[], authorize_url=url)

def truncate(s, l):
  return s[:l] + '...' if len(s) > l else s
#************************************************************************Perfil y Principal**********************************************************************************
class Principal(Handler):
	def get(self):
		mail = self.session.get('Correo')
		self.render("_base.html", correo=mail)

class Perfil(Handler):
	def get(self):
		mail = self.session.get('Correo')
		consulta=Usuarios.query(Usuarios.Correo==mail).get()
		self.render("perfil.html", correo=mail, datos=consulta)

class Principal2(Handler):
	def get(self):
		mail = self.session.get('Correo')
		self.render("_base2.html", correo=mail)

#************************************************************************Calendario**********************************************************************************

class Calendario(Handler):
    @decorator.oauth_required
    #Metodo get
    def get(self):
        mail = self.session.get('Correo')
        summary = []
        http=decorator.http()
        request=service_calendar.events().list(calendarId='primary')
        response_calendar=request.execute(http=http)

        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        eventsResult = service_calendar.events().list(
            calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
            orderBy='startTime').execute(http=http)
        events = eventsResult.get('items', [])
        logging.info(events)
        self.render("calendario.html", correo=mail,response_calendar=summary, eventos=events)
        if not events:
			logging.info('No upcoming events found.')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            logging.info(start, event['summary'])
            # print(start, event['summary'])

class CalendarioAdd(Handler):
	@decorator.oauth_required
	def post(self):
		http=decorator.http()
		mail = self.session.get('Correo')
		titulo = self.request.get('name')
		locacion = self.request.get('location')
		descripcion = self.request.get('des')
		fechaini = self.request.get('fechaini')
		horaini = self.request.get('horaini')
		fechafin = self.request.get('fechafin')
		horafin = self.request.get('horafin')
		if titulo == "" or locacion == "" or descripcion == "" or fechaini == "" or horaini == "" or fechafin == "" or horafin == "":
			self.redirect('/calendar')
		else:
			fechaini = fechaini+'T'+horaini+':00-06:00'
			fechafin = fechafin+'T'+horafin+':00-06:00'
			event = {
				'summary': titulo,
				'location': locacion,
				'description': descripcion,
				'start': {
					'dateTime': fechaini,
					'timeZone': 'America/Mexico_City',
				},
				'end': {
					'dateTime': fechafin,
					'timeZone': 'America/Mexico_City',
				},
				'attendees': [
					{'email': mail},
				],
				'reminders': {
					'useDefault': False,
					'overrides': [
						{'method': 'email', 'minutes': 24 * 60},
						{'method': 'popup', 'minutes': 10},
					],
				},
			}
			event = service_calendar.events().insert(calendarId='primary', body=event).execute(http=http)
			self.redirect('/calendar')

class CalendarioDel(Handler):
	@decorator.oauth_required
	def get(self):
		http=decorator.http()
		mail = self.session.get('Correo')
		idevent = self.request.get('idevent')
		service_calendar.events().delete(calendarId='primary', eventId=idevent).execute(http=http)
		self.redirect('/calendar')

#**********************************************************************Control Financiero**********************************************************************************

class Control(Handler):
    #Metodo get
	def get(self):
		mail = self.session.get('Correo')
		qry = Cuenta.query(Cuenta.Usuario == mail)
		ingre = 0
		qry2 = IngresoNDB.query(IngresoNDB.Usuario == mail)
		for resultado in qry2:
			ingre = resultado.Ingreso+ingre
		logging.info("Ingreso: " + str(ingre))
		egre = 0
		qry3 = EgresoNDB.query(EgresoNDB.Usuario == mail)
		for resultado in qry3:
			egre = resultado.Egreso+egre
		self.render("_basecuenta.html", correo=mail, cuentas=qry, ingreso=ingre, egreso=egre)

class CuentaNew(Handler):
	def get(self):
		mail = self.session.get('Correo')
		self.render("addcuenta.html", correo=mail)
	def post(self):
        #Obtener valores del formulario
		mail = self.session.get('Correo')
		name = self.request.get('cuenta')
		saldo = self.request.get('saldo')
		if name == "" or saldo == "":
			err = "Los campos no se llenaron correctamente"
			self.render("addcuenta.html", error=err, correo=mail)
		else:
			#Se crea ahora una entidad de tipo Usuarios y se escribe en el datastore.
			control = Cuenta(Usuario=mail,Nombre=name,Saldo=float(saldo))
			#El valor regresado por put es una llave, la cual puede ser usada para obtener nuevamente la misma entidad.
			cuentakey = control.put()
			#Obtengo la entidad
			control_user=cuentakey.get()
			if control_user == control:
				succ = "Cuenta Agregada"
				self.render("addcuenta.html", success=succ, correo=mail)

class Ingreso(Handler):
    #Metodo get
	def get(self):
		mail = self.session.get('Correo')
		qry = Cuenta.query(Cuenta.Usuario == mail)
		self.render("ingreso.html", correo=mail, cuentas=qry)
	def post(self):
		mail = self.session.get('Correo')
		fecha = self.request.get('fechain')
		saldo = self.request.get('saldo')
		cuenta = self.request.get('cuenta')
		cat = self.request.get('categoria')
		if fecha == "" or saldo == "" or cuenta == "" or cat == "":
			err = "Los campos no se llenaron correctamente"
			qry = Cuenta.query(Cuenta.Usuario == mail)
			self.render("ingreso.html", correo=mail, cuentas=qry, error=err)
		else:
			ing = IngresoNDB(Usuario=mail, Categoria=cat, Fecha=datetime.datetime.strptime(fecha, "%Y-%m-%d"), Ingreso=float(saldo), Cuenta=cuenta)
			cuentakey = ing.put()

			act = Cuenta.query(Cuenta.Nombre == cuenta).get()
			act.Saldo = act.Saldo + float(saldo)
			act.put()

			qry = Cuenta.query(Cuenta.Usuario == mail)
			succ = "Ingreso Agregado"
			self.render("ingreso.html", correo=mail, cuentas=qry, success=succ)

class Egreso(Handler):
    #Metodo get
	def get(self):
		mail = self.session.get('Correo')
		qry = Cuenta.query(Cuenta.Usuario == mail)
		self.render("egreso.html", correo=mail, cuentas=qry)
	def post(self):
		mail = self.session.get('Correo')
		fecha = self.request.get('fechaeg')
		saldo = self.request.get('saldo')
		cuenta = self.request.get('cuenta')
		cat = self.request.get('categoria')
		if fecha == "" or saldo == "" or cuenta == "" or cat == "":
			err = "Los campos no se llenaron correctamente"
			qry = Cuenta.query(Cuenta.Usuario == mail)
			self.render("egreso.html", correo=mail, cuentas=qry, error=err)
		else:
			egr = EgresoNDB(Usuario=mail, Categoria=cat, Fecha=datetime.datetime.strptime(fecha, "%Y-%m-%d"), Egreso=float(saldo), Cuenta=cuenta)
			cuentakey = egr.put()

			act = Cuenta.query(Cuenta.Nombre == cuenta).get()
			act.Saldo = act.Saldo - float(saldo)
			act.put()

			qry = Cuenta.query(Cuenta.Usuario == mail)
			succ = "Egreso Agregado"
			self.render("egreso.html", correo=mail, cuentas=qry, success=succ)

class Informes(Handler):
	def get(self):
		mail = self.session.get('Correo')
		qry = EgresoNDB.query(EgresoNDB.Usuario == mail)
		qry2 = IngresoNDB.query(IngresoNDB.Usuario == mail)
		self.render("informe.html", correo=mail, egresos=qry, ingreso=qry2)

class Va(Handler):
	def get(self):
		mail = self.session.get('Correo')
		qry = EgresoNDB.query(EgresoNDB.Usuario == mail)
		self.render("va.html", correo=mail, egresos=qry)

class Viene(Handler):
	def get(self):
		mail = self.session.get('Correo')
		qry2 = IngresoNDB.query(IngresoNDB.Usuario == mail)
		self.render("viene.html", correo=mail, ingreso=qry2)

class Proyecto(Handler):
    #Metodo get
    def get(self):
        mail = self.session.get('Correo')
        self.render("addproy.html", correo=mail)

class MailHandler(InboundMailHandler):
	def receive(self, mail_message):
		for content_type, pl in mail_message.bodies('text/plain'):
			mensaje = Correos(message_body=pl.payload.decode('utf-8'))
			mensaje.put()
		self.response.write("Gracias, su mensaje se ha enviado.")
		self.redirect('/')

#Clase del Notificador de rebote de cogheos
class LogBounceHandler(BounceNotificationHandler):
	def receive(self, bounce_message):
		logging.info('Received bounce post ... [%s]', self.request)
		logging.info('Bounce original: %s', bounce_message.original)
		logging.info('Bounce notification: %s', bounce_message.notification)

config = {}
config['webapp2_extras.sessions'] = {'secret_key': 'some-secret-key',}

app = webapp2.WSGIApplication([('/',Index),
				('/register',Registro),
				('/principal',Principal),
				('/logout',Logout),
				('/perfil',Perfil),
				('/principaladmin',Principal2),
				('/tarea',Tarea),
				('/proy',Proyecto),
				('/contacto',Contacto),
				('/tareasv',TareaView),
				('/taream',TareaUpd),
				('/tareab',TareaDel),
				('/tareast',TareaStatus),
				('/calendar',Calendario),
				('/calendaradd',CalendarioAdd),
				('/delevent',CalendarioDel),
				('/control',Control),
				('/cuentaa',CuentaNew),
				('/ingreso',Ingreso),
				('/egreso',Egreso),
				('/dondeva',Va),
				('/dondeviene',Viene),
				('/informes',Informes),
				(MailHandler.mapping()),
				(LogBounceHandler.mapping()),
				(decorator.callback_path, decorator.callback_handler())
				], debug=True, config=config)
