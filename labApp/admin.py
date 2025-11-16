from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.db import transaction, models
from .models import (
    Usuario, Laboratorio, Paciente, Pago, LoincCode, Analisis,
    ResultadoAnalisis, Plantilla, PropiedadPlantilla, IntervaloReferencia, Reporte
)

# -------------------------------
# Inlines
# -------------------------------
class IntervaloReferenciaInline(admin.TabularInline):
    model = IntervaloReferencia
    extra = 1  # Siempre mostrar un registro vacío para llenar

class PropiedadPlantillaInline(admin.TabularInline):
    model = PropiedadPlantilla
    fields = ('nombre_propiedad', 'unidad', 'loinc_code')
    autocomplete_fields = ('loinc_code',)  # Busca LOINC por texto
    extra = 1
    verbose_name = "Propiedad"
    verbose_name_plural = "Añadir Propiedades a esta Plantilla"

class ResultadoAnalisisInline(admin.TabularInline):
    model = ResultadoAnalisis
    extra = 0
    autocomplete_fields = ['loinc_code']
    fields = ('loinc_code', 'nombre_propiedad', 'valor', 'unidad', 'intervalo_referencia', 'valor_coloreado')
    readonly_fields = ('intervalo_referencia', 'valor_coloreado')

    def intervalo_referencia(self, obj):
        """Muestra el rango de referencia según paciente"""
        paciente = obj.analisis.paciente
        edad = paciente.edad
        sexo = paciente.sexo

        if edad <= 18:
            grupo_edad = "NINO"
        elif edad <= 59:
            grupo_edad = "ADULTO"
        else:
            grupo_edad = "ADULTO_MAYOR"

        # Buscar el intervalo correspondiente
        propiedad = obj.analisis.plantilla.propiedades.filter(nombre_propiedad=obj.nombre_propiedad).first()
        if not propiedad:
            return "-"
        intervalo = propiedad.intervalos.filter(
            grupo_edad=grupo_edad
        ).filter(
            models.Q(sexo=sexo) | models.Q(sexo="AMBOS")
        ).first()

        if intervalo:
            return f"{intervalo.valor_min} - {intervalo.valor_max} {obj.unidad or ''}"
        return "-"

    intervalo_referencia.short_description = "Rango Ref."

    def valor_coloreado(self, obj):
        """Muestra el valor con color según esté dentro o fuera del rango"""
        paciente = obj.analisis.paciente
        edad = paciente.edad
        sexo = paciente.sexo

        if edad <= 18:
            grupo_edad = "NINO"
        elif edad <= 59:
            grupo_edad = "ADULTO"
        else:
            grupo_edad = "ADULTO_MAYOR"

        propiedad = obj.analisis.plantilla.propiedades.filter(nombre_propiedad=obj.nombre_propiedad).first()
        if not propiedad:
            return obj.valor

        intervalo = propiedad.intervalos.filter(
            grupo_edad=grupo_edad
        ).filter(
            models.Q(sexo=sexo) | models.Q(sexo="AMBOS")
        ).first()

        if intervalo:
            try:
                valor = float(obj.valor)
                if valor < intervalo.valor_min or valor > intervalo.valor_max:
                    color = "red"
                else:
                    color = "green"
                return format_html('<span style="color:{};">{}</span>', color, obj.valor)
            except ValueError:
                return obj.valor  # Valor no numérico
        return obj.valor

    valor_coloreado.short_description = "Valor Coloreado"


# -------------------------------
# Admin de Plantilla
# -------------------------------
@admin.register(Plantilla)
class PlantillaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo_formato')
    search_fields = ('titulo',)
    list_filter = ('tipo_formato',)
    inlines = [PropiedadPlantillaInline]
    fieldsets = (
        (None, {'fields': ('titulo', 'tipo_formato')}),
        ('Contenido para Receta Justificada (Opcional)', {
            'classes': ('collapse',),
            'fields': ('texto_justificado_default',),
            'description': 'Este campo solo aplica si el formato es "Receta Justificada".'
        }),
    )

# -------------------------------
# Admin de PropiedadPlantilla
# -------------------------------
@admin.register(PropiedadPlantilla)
class PropiedadPlantillaAdmin(admin.ModelAdmin):
    list_display = ('nombre_propiedad', 'plantilla', 'unidad')
    search_fields = ('nombre_propiedad', 'plantilla__titulo')
    list_filter = ('plantilla',)
    autocomplete_fields = ('loinc_code',)
    inlines = [IntervaloReferenciaInline]

# -------------------------------
# Admin de Analisis
# -------------------------------
@admin.register(Analisis)
class AnalisisAdmin(admin.ModelAdmin):
    list_display = ('id', 'paciente', 'plantilla', 'fecha_analisis')
    search_fields = ('paciente__nombre', 'plantilla__titulo')
    list_filter = ('plantilla', 'fecha_analisis')
    inlines = [ResultadoAnalisisInline]
    raw_id_fields = ('paciente', 'plantilla')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # Crear resultados solo para análisis nuevos y con plantilla
        if not change and obj.plantilla and obj.plantilla.tipo_formato != 'RECETA_JUSTIFICADA':
            paciente = obj.paciente
            sexo_paciente = paciente.sexo
            if paciente.edad <= 18:
                grupo_edad = "NINO"
            elif paciente.edad <= 59:
                grupo_edad = "ADULTO"
            else:
                grupo_edad = "ADULTO_MAYOR"

            resultados = []
            for propiedad in obj.plantilla.propiedades.all():
                intervalo = propiedad.intervalos.filter(
                    grupo_edad=grupo_edad
                ).filter(
                    models.Q(sexo=sexo_paciente) | models.Q(sexo="AMBOS")
                ).first()

                if intervalo:
                    if not ResultadoAnalisis.objects.filter(
                        analisis=obj, nombre_propiedad=propiedad.nombre_propiedad
                    ).exists():
                        resultados.append(
                            ResultadoAnalisis(
                                analisis=obj,
                                loinc_code=propiedad.loinc_code,
                                nombre_propiedad=propiedad.nombre_propiedad,
                                valor='',
                                unidad=propiedad.unidad
                            )
                        )
            ResultadoAnalisis.objects.bulk_create(resultados)

# -------------------------------
# Admin de Usuario
# -------------------------------
class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = '__all__'
        widgets = {'password': forms.PasswordInput(render_value=True)}

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    form = UsuarioForm
    list_display = ('id', 'nombre', 'correo_electronico', 'num_telefono', 'is_active')
    search_fields = ('nombre', 'correo_electronico', 'laboratorios__nombre_laboratorio')
    filter_horizontal = ('laboratorios',)

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get('password'):
            obj.set_password(form.cleaned_data['password'])
        super().save_model(request, obj, form, change)

# -------------------------------
# Admin de Laboratorio
# -------------------------------
@admin.register(Laboratorio)
class LaboratorioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_laboratorio', 'ciudad', 'estado', 'pais', 'codigo_postal', 'logo_thumbnail')
    search_fields = ('nombre_laboratorio', 'ciudad', 'estado', 'pais')

    def logo_thumbnail(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" />', obj.logo.url)
        return "-"
    logo_thumbnail.short_description = 'Logo'

# -------------------------------
# Admin de Paciente
# -------------------------------
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'edad', 'sexo', 'laboratorio', 'telefono', 'correo_electronico')
    search_fields = ('nombre', 'laboratorio__nombre_laboratorio')
    list_filter = ('sexo', 'laboratorio')

# -------------------------------
# Admin de Pago
# -------------------------------
@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'fecha_pago', 'fecha_vencimiento', 'estado')
    list_filter = ('estado', 'fecha_pago', 'fecha_vencimiento')
    search_fields = ('usuario__nombre', 'usuario__correo_electronico')

# -------------------------------
# Admin de ResultadoAnalisis
# -------------------------------
@admin.register(ResultadoAnalisis)
class ResultadoAnalisisAdmin(admin.ModelAdmin):
    list_display = ('analisis', 'nombre_propiedad', 'valor', 'unidad')
    search_fields = ('nombre_propiedad', 'analisis__paciente__nombre')
    autocomplete_fields = ['loinc_code']

# -------------------------------
# Admin de LoincCode
# -------------------------------
@admin.register(LoincCode)
class LoincCodeAdmin(admin.ModelAdmin):
    list_display = ('loinc_num', 'shortname', 'component', 'property', 'system', 'scale_typ')
    search_fields = ('loinc_num', 'shortname', 'component', 'property')
    list_filter = ('system', 'scale_typ')
    ordering = ('loinc_num',)

# -------------------------------
# Admin de Reporte
# -------------------------------
from django.contrib import admin
from django.utils.html import format_html
from .models import Reporte

@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ("id", "analisis_str", "paciente_str", "usuario_str", "fecha_generacion", "ver_pdf")
    
    # Filtros válidos: solo campos existentes en el modelo o relacionados
    list_filter = ("fecha_generacion", "analisis__plantilla")
    
    search_fields = ("analisis__plantilla__titulo", "analisis__paciente__nombre", "usuario_generador__nombre")
    
    readonly_fields = ("analisis_str", "paciente_str", "usuario_str", "fecha_generacion")

    # Mostrar análisis
    @admin.display(description='Análisis')
    def analisis_str(self, obj):
        return str(obj.analisis)

    # Mostrar paciente
    @admin.display(description='Paciente')
    def paciente_str(self, obj):
        return str(obj.analisis.paciente)

    # Mostrar usuario generador
    @admin.display(description='Generado por')
    def usuario_str(self, obj):
        return str(obj.usuario_generador)

    # No permitir agregar desde admin
    def has_add_permission(self, request):
        return False

    # No permitir editar desde admin
    def has_change_permission(self, request, obj=None):
        return False

    # Permitir eliminar
    def has_delete_permission(self, request, obj=None):
        return True

    # Botón para ver PDF
    @admin.display(description='Preview PDF')
    def ver_pdf(self, obj):
        if obj.analisis:
            return format_html(
                '<a class="button" style="background-color:#2ecc71;color:white;padding:3px 8px;border-radius:4px;text-decoration:none;" '
                'href="/admin/reporte/{}/pdf/" target="_blank">🖨️ Ver PDF</a>', obj.id
            )
        return "-"
