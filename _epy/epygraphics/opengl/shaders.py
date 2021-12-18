import OpenGL.GL.shaders
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import freetype

global LOADED_CHARACTERS
LOADED_CHARACTERS = None

def getCharacters():
	global LOADED_CHARACTERS
	return LOADED_CHARACTERS

class CharacterSlot:
    def __init__(self, texture, glyph):
        self.texture = texture
        self.textureSize = (glyph.bitmap.width, glyph.bitmap.rows)

        if isinstance(glyph, freetype.GlyphSlot):
            self.bearing = (glyph.bitmap_left, glyph.bitmap_top)
            self.advance = glyph.advance.x
        elif isinstance(glyph, freetype.BitmapGlyph):
            self.bearing = (glyph.left, glyph.top)
            self.advance = None
        else:
            raise RuntimeError('unknown glyph type')

def load_shader(type="default"):
	if type == "gradient": return GEN_DEFAULT_SHADER_WITH_GRADIENT()
	if type == "text": return GEN_TEXT_SHADER()
	return GEN_DEFAULT_SHADER()
	
	
def GEN_DEFAULT_SHADER():
	#gl_Position = vec4(position+offset, 0.0, 1.0f);
	vertex_shader = """
	#version 330
	layout(location = 0) in vec2 position;
	layout(location = 1) in vec3 buffer_colors;
	layout(location = 2) in float offset_x;
	layout(location = 3) in float offset_y;
	out vec3 colors;
	uniform mat4 scale;
    void main()
    {
		colors = buffer_colors;
		gl_Position = gl_ModelViewProjectionMatrix  * vec4(position.x+(offset_x), position.y+offset_y, 0.0, 1.0f);
    }
    """
	#vertex_shader = vertex_shader.replace("\n", "")
	vertex_shader = vertex_shader.replace("\t", "")
	fragment_shader = """
    #version 330
    in vec3 colors;
    void main()
    {
		gl_FragColor = vec4(colors, 1.0);
    }
    """
	return vertex_shader, fragment_shader
	
	
def GEN_DEFAULT_SHADER_WITH_GRADIENT():
	print("Using gradient shader")
	vertex_shader = """
	#version 330
	layout(location = 0) in vec2 position;
	layout(location = 1) in vec3 buffer_colors;
	layout(location = 2) in vec2 offset;
	out vec3 colors;
	out vec2 TexCoords;
    void main()
    {
		colors = buffer_colors;
		gl_Position =  gl_ModelViewProjectionMatrix * vec4(position.x+offset.x, position.y+offset.y, 0.0, 1.0f);
		//gl_Position = gl_ModelViewProjectionMatrix * vec4(gl_FragCoord.xy, 0.0, 1.0f);
		TexCoords = vec2(position.x, position.y);
    }
    """
	fragment_shader = """
	#version 330
	in vec3 colors;
	out vec4 FragColor;

	in vec2 TexCoords;

	uniform sampler2D image;

	uniform bool horizontal;
	uniform float weight[5] = float[] (0.2270270270, 0.1945945946, 0.1216216216, 0.0540540541, 0.0162162162);

	void main()
	{             
		 FragColor = vec4(gl_FragCoord.xy, 0.0, 1.0);
	}
	"""
	fragment_shader = fragment_shader.replace("\t", "")
	return vertex_shader, fragment_shader
	
	
def GEN_TEXT_SHADER():
	VERTEX_SHADER = """
			#version 330 core
			layout (location = 0) in vec4 vertex; // <vec2 pos, vec2 tex>
			out vec2 TexCoords;

			uniform mat4 projection;

			void main()
			{
				gl_Position = projection * vec4(vertex.xy, 0.0, 1.0);
				TexCoords = vertex.zw;
			}
		   """

	FRAGMENT_SHADER = """
			#version 330 core
			in vec2 TexCoords;
			out vec4 color;

			uniform sampler2D text;
			uniform vec3 textColor;

			void main()
			{    
				vec4 sampled = vec4(1.0, 1.0, 1.0, texture(text, TexCoords).r);
				color = vec4(textColor, 1.0) * sampled;
			}
			"""
	return VERTEX_SHADER, FRAGMENT_SHADER

def load_ascii(vao, vbo, face):
	global LOADED_CHARACTERS
	Characters = {}
	for i in range(0,128):
		face.load_char(chr(i))
		glyph = face.glyph
		
		#generate texture
		texture = glGenTextures(1)
		glBindTexture(GL_TEXTURE_2D, texture)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, glyph.bitmap.width, glyph.bitmap.rows, 0,
					 GL_RED, GL_UNSIGNED_BYTE, glyph.bitmap.buffer)

		#texture options
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

		#now store character for later use
		Characters[chr(i)] = CharacterSlot(texture,glyph)
		
	glBindTexture(GL_TEXTURE_2D, 0)

	glBindVertexArray(vao)
	
	glBindBuffer(GL_ARRAY_BUFFER, vbo)
	glBufferData(GL_ARRAY_BUFFER, 6 * 4 * 4, None, GL_DYNAMIC_DRAW)
	glEnableVertexAttribArray(0)
	glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 0, None)
	glBindBuffer(GL_ARRAY_BUFFER, 0)
	glBindVertexArray(0)
	
	LOADED_CHARACTERS = Characters
	return Characters