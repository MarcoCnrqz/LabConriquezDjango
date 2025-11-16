# labApp/models.py

from django.db import models
from django.contrib.auth.hashers import make_password, check_password, is_password_usable
from django.db.models.signals import post_save
from django.dispatch import receiver

#------------------------------ Tabla Laboratorio ----------------------------
class Laboratorio(models.Model):
    nombre_laboratorio = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=20)
    pais = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='logos_laboratorios/', null=True, blank=True)
    def __str__(self):
        return f"{self.nombre_laboratorio} - {self.ciudad}, {self.estado}"

#------------------------------ Tabla Usuario ----------------------------
class Usuario(models.Model):
    nombre = models.CharField(max_length=150)
    correo_electronico = models.EmailField(unique=True)
    num_telefono = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    laboratorios = models.ManyToManyField(Laboratorio, related_name='usuarios', blank=True)

    def save(self, *args, **kwargs):
        if self.password and not is_password_usable(self.password):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()
    def check_password(self, raw_password):
        if not self.password: return False
        return check_password(raw_password, self.password)
    def __str__(self):
        return f"{self.nombre} ({self.correo_electronico})"

#------------------------ Tabla Paciente ------------------------------
class Paciente(models.Model):
    SEXO_CHOICES = [("MASCULINO", "Masculino"), ("FEMENINO", "Femenino")]
    laboratorio = models.ForeignKey(Laboratorio, on_delete=models.CASCADE, related_name="pacientes")
    nombre = models.CharField(max_length=150)
    edad = models.PositiveIntegerField()
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES)
    telefono = models.CharField(max_length=20)
    correo_electronico = models.EmailField(blank=True, null=True)
    def __str__(self):
        return f"{self.nombre} ({self.laboratorio.nombre_laboratorio})"

#--------------------------- Tabla Pagos ----------------------------
class Pago(models.Model):
    ESTADOS = [("PAGADO", "Pagado"), ("VENCIDO", "Vencido"), ("PENDIENTE", "Pendiente")]
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="pagos")
    fecha_pago = models.DateField()
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADOS)
    def __str__(self):
        return f"Pago {self.estado} - {self.usuario.nombre} ({self.fecha_pago})"

#------------------------ Tabla LOINC ------------------------------
class LoincCode(models.Model):
    loinc_num = models.CharField(max_length=20, unique=True)
    shortname = models.CharField(max_length=255, null=True, blank=True)
    component = models.TextField(null=True, blank=True)
    property = models.CharField(max_length=50, null=True, blank=True)
    system = models.CharField(max_length=100, null=True, blank=True)
    scale_typ = models.CharField(max_length=20, null=True, blank=True)
    def __str__(self):
        return f"{self.loinc_num} - {self.shortname}"

#=============================================================================
# SECCIÓN DE PLANTILLAS REESTRUCTURADA
#=============================================================================

# 1. El Fólder: La plantilla maestra que crea el administrador.
class Plantilla(models.Model):
    FORMATOS = [
        ('RESULTADOS', 'Resultados (Solo propiedades y valores)'),
        ('IMAGENES_RESULTADOS', 'Imágenes y Resultados'),
        ('RECETA_JUSTIFICADA', 'Receta Justificada (Solo texto)'),
    ]
    titulo = models.CharField(max_length=150, unique=True, help_text="Ej: Biometría Hemática")
    tipo_formato = models.CharField(max_length=50, choices=FORMATOS, default='RESULTADOS')
    texto_justificado_default = models.TextField(
        blank=True, null=True,
        help_text="Usado solo si el formato es 'Receta Justificada'"
    )

    def __str__(self):
        return self.titulo
    class Meta:
        verbose_name = "Plantilla de Análisis"
        verbose_name_plural = "1. Plantillas de Análisis (Crear aquí)"

# 2. Las Hojas: Las propiedades que van dentro de cada Fólder/Plantilla.
class PropiedadPlantilla(models.Model):
    plantilla = models.ForeignKey(Plantilla, on_delete=models.CASCADE, related_name="propiedades")
    nombre_propiedad = models.CharField(max_length=100, help_text="Ej: Hemoglobina, Glucosa")
    loinc_code = models.ForeignKey(LoincCode, on_delete=models.PROTECT, null=True, blank=True)
    unidad = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.plantilla.titulo} - {self.nombre_propiedad}"
    class Meta:
        verbose_name = "Propiedad de Plantilla"
        verbose_name_plural = "2. Propiedades de Plantillas (Añadir Intervalos aquí)"

# 3. Los Intervalos: Se asocian a cada Hoja/Propiedad.
class IntervaloReferencia(models.Model):
    propiedad = models.ForeignKey(PropiedadPlantilla, on_delete=models.CASCADE, related_name="intervalos")
    EDADES = [("NINO", "Niño"), ("ADULTO", "Adulto"), ("ADULTO_MAYOR", "Adulto Mayor")]
    SEXOS = [("MASCULINO", "Masculino"), ("FEMENINO", "Femenino"), ("AMBOS", "Ambos")]
    grupo_edad = models.CharField(max_length=20, choices=EDADES)
    sexo = models.CharField(max_length=10, choices=SEXOS, default="AMBOS")
    valor_min = models.FloatField()
    valor_max = models.FloatField()

    def __str__(self):
        return f"{self.propiedad.nombre_propiedad} ({self.grupo_edad}, {self.sexo})"

#=============================================================================
# SECCIÓN DE ANÁLISIS DEL PACIENTE
#=============================================================================

# 4. El Análisis: Se vincula a la Plantilla maestra.
class Analisis(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    plantilla = models.ForeignKey(Plantilla, on_delete=models.PROTECT, related_name='analisis', null=True, blank=True)
    fecha_analisis = models.DateTimeField(auto_now_add=True)
    fecha_muestra = models.DateField(null=True, blank=True)
    hora_toma = models.TimeField(null=True, blank=True)
    hora_impresion = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.plantilla.titulo} - {self.paciente.nombre}" if self.plantilla else "Análisis sin plantilla"

# 5. Los Resultados: Se generan a partir del Análisis.
class ResultadoAnalisis(models.Model):
    analisis = models.ForeignKey(Analisis, on_delete=models.CASCADE, related_name='resultados')
    loinc_code = models.ForeignKey(LoincCode, on_delete=models.PROTECT, null=True, blank=True)
    nombre_propiedad = models.CharField(max_length=100)
    valor = models.CharField(max_length=100, blank=True)
    unidad = models.CharField(max_length=20, null=True, blank=True)
    def __str__(self):
        return f"{self.nombre_propiedad}: {self.valor} {self.unidad or ''}"

# 6. El Disparador: Se actualiza para usar la nueva estructura.
@receiver(post_save, sender=Analisis)
def crear_resultados_predeterminados(sender, instance, created, **kwargs):
    if created and instance.plantilla and instance.plantilla.tipo_formato != 'RECETA_JUSTIFICADA':
        paciente = instance.paciente
        sexo_paciente = paciente.sexo
        if paciente.edad <= 18: grupo_edad = "NINO"
        elif paciente.edad <= 59: grupo_edad = "ADULTO"
        else: grupo_edad = "ADULTO_MAYOR"

        for propiedad in instance.plantilla.propiedades.all():
            intervalo = propiedad.intervalos.filter(grupo_edad=grupo_edad).filter(models.Q(sexo=sexo_paciente) | models.Q(sexo="AMBOS")).first()
            if intervalo:
                ResultadoAnalisis.objects.create(
                    analisis=instance,
                    loinc_code=propiedad.loinc_code,
                    nombre_propiedad=propiedad.nombre_propiedad,
                    valor='',
                    unidad=propiedad.unidad
                )

#------------------------ Tabla Reporte ------------------------------
class Reporte(models.Model):
    analisis = models.ForeignKey(Analisis, on_delete=models.CASCADE, related_name="reportes")
    generado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reporte: {self.analisis.paciente.nombre} - {self.analisis.plantilla.titulo} ({self.fecha_generacion:%d-%m-%Y})"
