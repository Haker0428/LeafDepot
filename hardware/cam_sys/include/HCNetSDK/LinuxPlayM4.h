#ifndef __LINUX_PLAYM4_H__
#define __LINUX_PLAYM4_H__

#ifdef __cplusplus
	extern "C" 
	{
#endif

typedef unsigned int PLAYM4_HWND;
typedef void * PLAYM4_HWNDEX;
typedef void * PLAYM4_HDC;

#define PLAYM4_API 

#define __stdcall

#ifndef CALLBACK
#define CALLBACK
#endif

//Max channel numbers
#define PLAYM4_MAX_SUPPORTS 500

//Wave coef range;
#define MIN_WAVE_COEF -100
#define MAX_WAVE_COEF 100

//Timer type
#define TIMER_1 1 //Only 16 timers for every process.Default TIMER;
#define TIMER_2 2 //Not limit;But the precision less than TIMER_1; 

//BUFFER AND DATA TYPE
#define BUF_VIDEO_SRC               (1) //mixed input,total src buffer size;splited input,video src buffer size 
#define BUF_AUDIO_SRC               (2) //mixed input,not defined;splited input,audio src buffer size
#define BUF_VIDEO_RENDER            (3) //video render node count or node cout for decoded data
#define BUF_AUDIO_RENDER            (4) //audio render node count 
#define BUF_VIDEO_DECODED           (5) //video decoded node count to render
#define BUF_AUDIO_DECODED           (6) //audio decoded node count to render
#define BUF_VIDEO_SRC_EX            (7)

//Error code
#define  PLAYM4_NOERROR					0	//no error
#define	 PLAYM4_PARA_OVER				1	//input parameter is invalid;
#define  PLAYM4_ORDER_ERROR				2	//The order of the function to be called is error.
#define	 PLAYM4_TIMER_ERROR				3	//Create multimedia clock failed;
#define  PLAYM4_DEC_VIDEO_ERROR			4	//Decode video data failed.
#define  PLAYM4_DEC_AUDIO_ERROR			5	//Decode audio data failed.
#define	 PLAYM4_ALLOC_MEMORY_ERROR		6	//Allocate memory failed.
#define  PLAYM4_OPEN_FILE_ERROR			7	//Open the file failed.
#define  PLAYM4_CREATE_OBJ_ERROR		8	//Create thread or event failed
//#define  PLAYM4_CREATE_DDRAW_ERROR		9	//Create DirectDraw object failed.
//#define  PLAYM4_CREATE_OFFSCREEN_ERROR 10	//failed when creating off-screen surface.
#define  PLAYM4_BUF_OVER			   11	//buffer is overflow
#define  PLAYM4_CREATE_SOUND_ERROR	   12	//failed when creating audio device.	
#define	 PLAYM4_SET_VOLUME_ERROR	   13	//Set volume failed
#define  PLAYM4_SUPPORT_FILE_ONLY	   14	//The function only support play file.
#define  PLAYM4_SUPPORT_STREAM_ONLY	   15	//The function only support play stream.
#define  PLAYM4_SYS_NOT_SUPPORT		   16	//System not support.
#define  PLAYM4_FILEHEADER_UNKNOWN     17	//No file header.
#define  PLAYM4_VERSION_INCORRECT	   18	//The version of decoder and encoder is not adapted.  
#define  PLAYM4_INIT_DECODER_ERROR     19	//Initialize decoder failed.
#define  PLAYM4_CHECK_FILE_ERROR	   20	//The file data is unknown.
#define  PLAYM4_INIT_TIMER_ERROR	   21	//Initialize multimedia clock failed.
#define	 PLAYM4_BLT_ERROR		       22	//Display failed.
//#define  PLAYM4_UPDATE_ERROR		   23	//Update failed.
#define  PLAYM4_OPEN_FILE_ERROR_MULTI  24   //openfile error, streamtype is multi
#define  PLAYM4_OPEN_FILE_ERROR_VIDEO  25   //openfile error, streamtype is video
#define  PLAYM4_JPEG_COMPRESS_ERROR    26   //JPEG compress error
#define  PLAYM4_EXTRACT_NOT_SUPPORT    27	//Don't support the version of this file.
#define  PLAYM4_EXTRACT_DATA_ERROR     28	//extract video data failed.
#define  PLAYM4_SECRET_KEY_ERROR       29	//Secret key is error //add 20071218
#define  PLAYM4_DECODE_KEYFRAME_ERROR  30   //add by hy 20090318
#define  PLAYM4_NEED_MORE_DATA         31   //add by hy 20100617
#define  PLAYM4_INVALID_PORT		   32	//add by cj 20100913
#define  PLAYM4_NOT_FIND               33	//add by cj 20110428
#define  PLAYM4_NEED_LARGER_BUFFER     34  //add by pzj 20130528
#define  PLAYM4_FAIL_UNKNOWN		   99   //Fail, but the reason is unknown;	

//���۹��ܴ�����
#define PLAYM4_FEC_ERR_ENABLEFAIL				100 // ����ģ�����ʧ��
#define PLAYM4_FEC_ERR_NOTENABLE				101 // ����ģ��û�м���
#define PLAYM4_FEC_ERR_NOSUBPORT				102 // �Ӷ˿�û�з���
#define PLAYM4_FEC_ERR_PARAMNOTINIT				103 // û�г�ʼ����Ӧ�˿ڵĲ���
#define PLAYM4_FEC_ERR_SUBPORTOVER				104 // �Ӷ˿��Ѿ�����
#define PLAYM4_FEC_ERR_EFFECTNOTSUPPORT			105 // �ð�װ��ʽ������Ч����֧��
#define PLAYM4_FEC_ERR_INVALIDWND				106 // �Ƿ��Ĵ���
#define PLAYM4_FEC_ERR_PTZOVERFLOW				107 // PTZλ��Խ��
#define PLAYM4_FEC_ERR_RADIUSINVALID			108 // Բ�Ĳ����Ƿ�
#define PLAYM4_FEC_ERR_UPDATENOTSUPPORT			109 // ָ���İ�װ��ʽ�ͽ���Ч�����ò������²�֧��
#define PLAYM4_FEC_ERR_NOPLAYPORT				110 // ���ſ�˿�û������
#define PLAYM4_FEC_ERR_PARAMVALID				111 // ����Ϊ��
#define PLAYM4_FEC_ERR_INVALIDPORT				112 // �Ƿ��Ӷ˿�
#define PLAYM4_FEC_ERR_PTZZOOMOVER				113 // PTZ������ΧԽ��
#define PLAYM4_FEC_ERR_OVERMAXPORT				114  // ����ͨ�����ͣ����֧�ֵĽ���ͨ��Ϊ�ĸ�
#define PLAYM4_FEC_ERR_ENABLED                  115  //�ö˿��Ѿ�����������ģ��
#define PLAYM4_FEC_ERR_D3DACCENOTENABLE			116 // D3D����û�п���
#define PLAYM4_FEC_ERR_PLACETYPE                117 // ��װ��ʽ����.һ�����ſ�port����Ӧһ�ְ�װ��ʽ
#define PLAYM4_FEC_ERR_CorrectType              118 // ������ʽ�����������ʽ����,���ܿ����������һ�����ſ�port,�趨����PTZ�����۰��������ʽ��,�����Ľ�����ʽ��ֻ�ܿ�һ·;����180�Ƚ������ܺ�ptz����һ�𿪣���������������������޹����ԡ�
#define PLAYM4_FEC_ERR_NULLWND                  119 // ���۴���Ϊ��
#define PLAYM4_FEC_ERR_PARA                     120 // ���۲�������

//Max display regions.
#define MAX_DISPLAY_WND 4

//Display type
#define DISPLAY_NORMAL            0x00000001
#define DISPLAY_QUARTER           0x00000002
#define DISPLAY_YC_SCALE          0x00000004	//add by gb 20091116
#define DISPLAY_NOTEARING         0x00000008
//Display buffers
#define MAX_DIS_FRAMES 50
#define MIN_DIS_FRAMES 1

//Locate by
#define BY_FRAMENUM  1
#define BY_FRAMETIME 2

//Source buffer
#define SOURCE_BUF_MAX	1024*100000
#define SOURCE_BUF_MIN	1024*50

//Stream type
#define STREAME_REALTIME 0
#define STREAME_FILE	 1

//frame type
#define T_AUDIO16	101
#define T_AUDIO8	100
#define T_UYVY		1
#define T_YV12		3
#define T_RGB32		7

//capability
#define SUPPORT_DDRAW		1 
#define SUPPORT_BLT         2 
#define SUPPORT_BLTFOURCC   4 
#define SUPPORT_BLTSHRINKX  8 
#define SUPPORT_BLTSHRINKY  16
#define SUPPORT_BLTSTRETCHX 32
#define SUPPORT_BLTSTRETCHY 64
#define SUPPORT_SSE         128
#define SUPPORT_MMX			256 

// ���º궨������HIK_MEDIAINFO�ṹ
#define FOURCC_HKMI			0x484B4D49	// "HKMI" HIK_MEDIAINFO�ṹ���
// ϵͳ��װ��ʽ	
#define SYSTEM_NULL			0x0				// û��ϵͳ�㣬����Ƶ������Ƶ��	
#define SYSTEM_HIK          0x1				// ���������ļ���
#define SYSTEM_MPEG2_PS     0x2				// PS��װ
#define SYSTEM_MPEG2_TS     0x3				// TS��װ
#define SYSTEM_RTP          0x4				// rtp��װ
#define SYSTEM_RTMP         0xD         // rtmp��װ
#define SYSTEM_RTPHIK       0x401       // rtp��װhik
#define SYSTEM_RTP_JT       0x104       // rtpjt��װ
#define SYSTEM_DAH          0x8001     ///< �󻪷�װ

// ��Ƶ��������
#define VIDEO_NULL          0x0 // û����Ƶ
#define VIDEO_H264          0x1 // ��������H.264
#define VIDEO_MPEG2			0x2	// ��׼MPEG2
#define VIDEO_MPEG4         0x3 // ��׼MPEG4
#define VIDEO_MJPEG			0x4
#define VIDEO_AVC265        0x5 // ��׼H265/AVC
#define VIDEO_SVAC          0x6
#define VIDEO_AVC264        0x0100

// ��Ƶ��������
#define AUDIO_NULL          0x0000 // û����Ƶ
#define AUDIO_ADPCM         0x1000 // ADPCM 
#define AUDIO_MPEG          0x2000 // MPEG ϵ����Ƶ��������������Ӧ����MPEG��Ƶ
#define AUDIO_AAC           0x2001
#define AUDIO_RAW_DATA8     0x7000 //������Ϊ8k��ԭʼ����
#define AUDIO_RAW_UDATA16   0x7001 //������Ϊ16k��ԭʼ���ݣ���L16
// Gϵ����Ƶ
#define AUDIO_RAW_DATA8		0x7000      //������Ϊ8k��ԭʼ����
#define AUDIO_RAW_UDATA16	0x7001      //������Ϊ16k��ԭʼ���ݣ���L16
#define AUDIO_G711_U		0x7110
#define AUDIO_G711_A		0x7111
#define AUDIO_G722_1		0x7221
#define AUDIO_G723_1        0x7231
#define AUDIO_G726_U        0x7260
#define AUDIO_G726_A        0x7261
#define AUDIO_G726_16       0x7262
#define AUDIO_G729          0x7290
#define AUDIO_AMR_NB		0x3000

#define SYNCDATA_VEH	    1 //ͬ������:������Ϣ	
#define SYNCDATA_IVS	    2 //ͬ������:������Ϣ

//motion flow type
#define	MOTION_FLOW_NONE			0
#define MOTION_FLOW_CPU				1
#define MOTION_FLOW_GPU				2

//����Ƶ��������
#define ENCRYPT_AES_3R_VIDEO     1
#define ENCRYPT_AES_10R_VIDEO    2
#define ENCRYPT_AES_3R_AUDIO     1
#define ENCRYPT_AES_10R_AUDIO    2

typedef struct tagSystemTime
{
    short wYear;
    short wMonth;
    short wDayOfWeek;
    short wDay;
    short wHour;
    short wMinute;
    short wSecond;
    short wMilliseconds;
}SYSTEMTIME;

typedef struct tagHKRect
{
    unsigned long left;
    unsigned long top;
    unsigned long right;
    unsigned long bottom;
}HKRECT;

//Frame position
typedef struct
{
	long long nFilePos;
    int nFrameNum;
    int nFrameTime;
    int nErrorFrameNum;
    SYSTEMTIME *pErrorTime;
    int nErrorLostFrameNum;
    int nErrorFrameSize;
}FRAME_POS,*PFRAME_POS;

//Frame Info
typedef struct
{
    int nWidth;
    int nHeight;
    int nStamp;
    int nType;
    int nFrameRate;
    unsigned int dwFrameNum;
}FRAME_INFO;

//Frame 
typedef struct
{
    char *pDataBuf;
    int  nSize;
    int  nFrameNum;
    int  bIsAudio;
    int  nReserved;
}FRAME_TYPE;

//Watermark Info	//add by gb 080119
typedef struct
{
    char *pDataBuf;
    int  nSize;
    int  nFrameNum;
    int  bRsaRight;
    int  nReserved;
}WATERMARK_INFO;

typedef struct SYNCDATA_INFO 
{
    unsigned int dwDataType;        //����������ͬ���ĸ�����Ϣ���ͣ�Ŀǰ�У�������Ϣ��������Ϣ
    unsigned int dwDataLen;         //������Ϣ���ݳ���
    unsigned char* pData;           //ָ������Ϣ���ݽṹ��ָ��,����IVS_INFO�ṹ
} SYNCDATA_INFO;

typedef struct _VCA_RECT_F_
{
    float x;         //�������Ͻ�X������
    float y;         //�������Ͻ�Y������
    float width;     //���ο��
    float height;    //���θ߶�
}VCA_RECT_F;

//Ŀ����Ϣ�ṹ��
typedef struct _VCA_TARGET_EX
{
    unsigned int      ID;          //ID
    unsigned char     reserved[8]; //�����ֽ�
    VCA_RECT_F        rect;        //Ŀ���
    unsigned char     reserved1[40]; //˽����Ϣ��չ�ֶΣ���ʱ��unsigned char�����ʾ������ⲿ�������ٸ�֪����ṹ����Ϣ
}VCA_TARGET_EX;

typedef struct _VCA_TARGET_LIST_EX
{
    unsigned int    target_num;             //Ŀ������
    VCA_TARGET_EX   *pstTarget;             //Ŀ�����ݣ�����VCA_TARGET_EX�Ĵ�С����ƫ�ƶ�ȡ����Ŀ��������Ϣ����
}VCA_TARGET_LIST_EX;

//������Ϣ�ṹ��ص���
typedef struct _INTEL_INFO_EX
{
    unsigned int                   type;               ///< ��ǻص�������Щ˽����Ϣ����
    VCA_TARGET_LIST_EX             stTarget;           ///< Ŀ��
    VCA_TARGET_LIST_EX             stTarget_EX;        ///< ��������Ŀ��
}INTEL_INFO_EX;

/////////////////////////////////////////////////////////////////////////////////////////////
//IVS��������Ϣ�ص��ӿڽṹ�嶨��
/////////////////////////////////////////////////////////////////////////////////////////////

///                                Ŀ���                           ///
typedef struct _VCA_POINT_F_
{
    float x;
    float y;
}VCA_POINT_F;

//�����(������)
typedef struct _VCA_POLYGON_F_
{
    unsigned int  vertex_num;                  //������
    VCA_POINT_F   point[10];   //����
}VCA_POLYGON_F;

//��ת����
typedef struct _VCA_ROTATE_RECT_F_
{
    float				  cx;						// �������ĵ�X������
    float				  cy;						// �������ĵ�Y������
    float				  width;					// ���ο��
    float				  height;					// ���θ߶�
    float				  theta;				   // ��ת���νǶ�
}VCA_ROTATE_RECT_F;

//����������
typedef struct _VCA_REGION_
{
    unsigned int region_type;           // �ο�VCA_REGION_TYPE��2��ʾ����Σ�3��ʾ����
    char         reserved[12];
    union
    {
        unsigned char		size[84];
        VCA_POLYGON_F       polygon;                // �����
        VCA_RECT_F          rect;                   // ����
        VCA_ROTATE_RECT_F 	rotate_rect;	 		 // ��ת����,�ݲ�֧��
    };
}VCA_REGION;

//����Ŀ���ṹ��
typedef struct 
{
    unsigned int            id;
    unsigned int            blob_type;        // Ŀ����_OBJ_TYPE
    short                   confidence;       // Ŀ������Ŷ�
    char                    reserved[14];
    VCA_REGION              region;           // Ŀ��λ������
    unsigned char           privt_info[40];   // ��չ��Ϣ
}HIK_TARGET_BLOB_EX;

//Ŀ����б���Ϣ���壺
typedef struct _VCA_TARGET_LIST_V1_EX_
{
    unsigned int         LineType;      //�����ͣ�0��ʾ���ο�1��ʾ�Ľǿ�
    unsigned int         target_num;    //Ŀ������
    HIK_TARGET_BLOB_EX   *pstTarget;    //Ŀ�����ݣ�����HIK_TARGET_BLOB_EX�Ĵ�С����ƫ�ƶ�ȡ����Ŀ��������Ϣ����
}VCA_TARGET_LIST_V1_EX;

///                                �����                           ///
//���������ṹ��
typedef struct _VCA_RULE_EX
{
    unsigned char       ID;               //����ID
    unsigned char       reserved[15];       //�����ֽ�
    VCA_POLYGON_F       polygon;         //�����Ӧ�Ķ��������
    unsigned char       privt_info[40];      // ��չ��Ϣ
}VCA_RULE_EX;

//������б���Ϣ���壺
typedef struct _VCA_RULE_LIST_V3_EX_
{
    unsigned int  LineType;      //�����ͣ�0��ʾ���ο�1 ��ʾ�Ľǿ�
    unsigned int  rule_num;     //�����й�������
    VCA_RULE_EX   *pstRule;   //�������ݣ�����VCA_RULE_EX�Ĵ�С����ƫ�ƶ�ȡ����Ŀ��������Ϣ����
}VCA_RULE_LIST_V3_EX;

///                                ������                           ///

typedef struct  _VCA_ALERT_EX_
{
    unsigned char     alert;           //���ޱ�����Ϣ: 0-û�У�1-��
    unsigned char     reserved[7];     //�����ֽ�
    VCA_RULE_EX       rule_info;       //����������Ϣ
    VCA_TARGET_EX        target;          //����Ŀ����Ϣ
    unsigned char     privt_info[40];  // ��չ��Ϣ
}VCA_ALERT_EX;

//������Ϣ���壺
typedef struct  _VCA_ALERT_LIST_EX_
{
    unsigned int           alert_num;  //��������
    VCA_ALERT_EX           *pstAlert; 
}VCA_ALERT_LIST_EX;

//������Ϣ�ṹ��ص���
typedef struct _PRIVATE_INFO_
{
    unsigned int                  type;    ///< ��ǻص�������Щ˽����Ϣ����
    VCA_TARGET_LIST_V1_EX         stTarget;           ///< ��ͨĿ������� 1
    VCA_TARGET_LIST_V1_EX         stTarget_EX;        ///< ��������Ŀ������� 2
    VCA_RULE_LIST_V3_EX           stRule;             ///< ��ͨ��������� 4
    VCA_RULE_LIST_V3_EX           stRule_EX;          ///< ����������������� 8
    VCA_ALERT_LIST_EX             stAlert;            ///< ������Ϣ������ 16
} PRIVATE_INFO;

/////////////////////////////////////////////////////////////////////////////////////////////

#ifndef _HIK_MEDIAINFO_FLAG_
#define _HIK_MEDIAINFO_FLAG_
typedef struct _HIK_MEDIAINFO_				// modified by gb 080425
{
    unsigned int    media_fourcc;			// "HKMI": 0x484B4D49 Hikvision Media Information
    unsigned short  media_version;			// �汾�ţ�ָ����Ϣ�ṹ�汾�ţ�ĿǰΪ0x0101,��1.01�汾��01�����汾�ţ�01���Ӱ汾�š�
    unsigned short  device_id;				// �豸ID�����ڷ���			

    unsigned short  system_format;          // ϵͳ��װ��
    unsigned short  video_format;           // ��Ƶ��������

    unsigned short  audio_format;           // ��Ƶ��������
    unsigned char   audio_channels;         // ͨ����  
    unsigned char   audio_bits_per_sample;  // ��λ��
    unsigned int    audio_samplesrate;      // ������ 
    unsigned int    audio_bitrate;          // ѹ����Ƶ����,��λ��bit
    unsigned char   flag; //8bit,0x81��ʾ�� smart��ǣ�����Ϊ��smart,����ʶ��intra�ķ�ʽ�� media_version >= 0x0103&& video_fortmat = (H.264 or H.265) && ((flag & 0x02) ==0x2) 
    unsigned char   stream_tag; //8bit,0x81��ʾ�����к���SDP��Ϣ 
    unsigned char   reserved[14]; // ���� 
}HIK_MEDIAINFO;
#endif

typedef struct  
{
    int nPort;
    char* pBuf;
    int nBufLen;
    int nWidth;
    int nHeight;
    int nStamp;
    int nType;
    void* nUser;
}DISPLAY_INFO;

typedef struct
{
    int nPort;
    char *pVideoBuf;
    int nVideoBufLen;
    char *pPriBuf;
    int nPriBufLen;
    int nWidth;
    int nHeight;
    int nStamp;
    int nType;
    void* nUser;
}DISPLAY_INFOEX;

typedef struct
{
    long         nPort;        //ͨ����
    char         *pBuf;        //���صĵ�һ·ͼ������ָ��
    unsigned int nBufLen;      //���صĵ�һ·ͼ�����ݴ�С
    char         *pBuf1;       //���صĵڶ�·ͼ������ָ��
    unsigned int nBufLen1;     //���صĵڶ�·ͼ�����ݴ�С
    char         *pBuf2;       //���صĵ���·ͼ������ָ��
    unsigned int nBufLen2;     //���صĵ���·ͼ�����ݴ�С
    unsigned int nWidth;       //�����
    unsigned int nHeight;      //�����
    unsigned int nStamp;       //ʱ����Ϣ����λ����
    unsigned int nType;        //��������
    void         *pUser;       //�û�����
    unsigned int reserved[4];  //������reserve[0]���ڱ���ص���֡��
}DISPLAY_INFO_YUV;

typedef struct PLAYM4_SYSTEM_TIME //����ʱ�� 
{
    unsigned int dwYear; //��
    unsigned int dwMon;  //��
    unsigned int dwDay;  //��
    unsigned int dwHour; //ʱ
    unsigned int dwMin;  //��
    unsigned int dwSec;  //��
    unsigned int dwMs;   //����
} PLAYM4_SYSTEM_TIME;

#ifndef CROP_PIC_INFO_TAG
#define CROP_PIC_INFO_TAG
typedef struct
{
    unsigned char* pDataBuf;      //ץͼ����buffer
    unsigned int   dwPicSize;	  //ʵ��ͼƬ��С
    unsigned int   dwBufSize;      //����buffer��С
    unsigned int   dwPicWidth;	  //��ͼ��
    unsigned int   dwPicHeight;    //��ͼ��
    unsigned int   dwReserve;      //���һ��reserve�ֶ�
    HKRECT*        pCropRect;     //ѡ������NULL, ͬ�ϵ�ץͼ�ӿ�
}CROP_PIC_INFO;
#endif

///<��Ⱦ��ʾ��ؽӿ�
#ifndef PLAYM4_HIKD3D11_TAG
#define PLAYM4_HIKD3D11_TAG

///<Ӳ����̽��ֱ���
#define HXVA_RESOLUTION_NONE   0x00      // 0
#define HXVA_RESOLUTION_200W   0x01      // 1920*1080
#define HXVA_RESOLUTION_300W   0x02      // 2048*1536
#define HXVA_RESOLUTION_500W   0x03      // 2560*1920
#define HXVA_RESOLUTION_800W   0x04      // 3840*2160
#define HXVA_RESOLUTION_1600W  0x05      // 4096*4096
#define HXVA_RESOLUTION_6400W  0x06      // 8192*8192(H.265)

///<Ӳ�������Ⱦ������̽������ṹ��
typedef struct _tagHDECODESUPPORT_
{
    unsigned char  chGPUType;            // GPU���ͣ� 0-�ޣ�1-N�����ԣ�2-A�����ԣ�3-Intel����
    unsigned char  bDXVA_D3D9;           // windows �ж��Ƿ�֧��DXVA_D3D9Ӳ����:0-��֧�֣�1-֧��
    unsigned char  bCUVID_D3D11;         // windows �ж��Ƿ�֧��CUVID_D3D11Ӳ����:0-��֧�֣�1-֧��
    unsigned char  chDXVAH264_Max_Resolution;// windows DXVA,h264����֧�ֵ����ķֱ��ʴ��ֵ-���Ǿ�׼ֵ����λ���򣩣����嶨���ö������
    unsigned char  chDXVAH265_Max_Resolution;// windows DXVA,h265����֧�ֵ����ķֱ��ʴ��ֵ-���Ǿ�׼ֵ����λ���򣩣����嶨���ö������
    unsigned char  chCUVIDH264_Max_Resolution;// windows CUVID,h264����֧�ֵ����ķֱ��ʴ��ֵ-���Ǿ�׼ֵ����λ���򣩣����嶨���ö������
    unsigned char  chCUVIDH265_Max_Resolution;// windows CUVID,h265����֧�ֵ����ķֱ��ʴ��ֵ-���Ǿ�׼ֵ����λ���򣩣����嶨���ö������
    unsigned char  chHXVAH264_Max_Resolution;// Linux  HXVA,h264����֧�ֵ����ķֱ��ʴ��ֵ-���Ǿ�׼ֵ����λ���򣩣����嶨���ö������
    unsigned char  chHXVAH265_Max_Resolution;// Linux HXVA,h265����֧�ֵ����ķֱ��ʴ��ֵ-���Ǿ�׼ֵ����λ���򣩣����嶨���ö������
    unsigned char  chValidFlag;          ///<��Ч
    unsigned char  bD3D11VA;             // windows �ж��Ƿ�֧��D3D11VAӲ����:0-��֧�֣�1-֧��
    unsigned char  chD3D11VAH264_Max_Resolution;// windows D3D11VA,h264����֧�ֵ����ķֱ��ʴ��ֵ-���Ǿ�׼ֵ�����嶨���ö������
    unsigned char  chD3D11VAH265_Max_Resolution;// windows D3D11VA,h265����֧�ֵ����ķֱ��ʴ��ֵ-���Ǿ�׼ֵ�����嶨���ö������
    unsigned char  nReserved[9];        // �����ֶ�
}HDECODESUPPORT;///< Ӳ����֧����Ϣ

typedef struct _tagRENDERSUPPORT_
{
    unsigned char  bDDraw;              ///< windows �ж��Ƿ�֧��Draw��Ⱦ
    unsigned char  bD3D9Surface;        ///< windows �ж��Ƿ�֧��D3D9������Ⱦ
    unsigned char  bD3D9Texture;        ///< windows �ж��Ƿ�֧��D3D9������Ⱦ
    unsigned char  bD3D11;              ///< windows �ж��Ƿ�֧��D3D11��Ⱦ
    unsigned char  chValidFlag;         ///<��Ч
    unsigned char  nGPUType;            ///< ��Ⱦ̽��GPU����  0-��; 1-Intel;2-NVIDIA;3-AMD;4-BASIC��Ӳ��̽��gpu�����в���
    unsigned char  nReserved[10];       ///< �����ֶ�
}RENDERSUPPORT;///< ��Ⱦ֧����Ϣ  

typedef struct _tagENGINESUPPORT_
{
    HDECODESUPPORT stHDecodeSupport; ///<Ӳ����������
    RENDERSUPPORT  stRenderSupport;  ///<��Ⱦ������
    unsigned char  chDeviceCount;    ///<�Կ����������ͬһ�����Կ�����-���˵���ͬ�����Կ���
    unsigned char  chReserved[15];    ///<�����ֶ�
}ENGINESUPPORT;///< Ӳ�������Ⱦ֧��������

///<��Ⱦץͼ�ṹ��
typedef struct _tagD3D11_PIC_INFO_
{
    unsigned int   nPicMode;     //ץͼģʽ��0-��������ʵ�ʷֱ���ץͼ(֮ǰץͼģʽ)��1-�������洫��Ŀ��ץͼ��nPicWidth*nPicHeightΪ��ʾ���ڿ��ʱЧ����ѣ�
    unsigned char* pBuf;         //ץͼ����buffer
    unsigned int   nBufSize;     //����buffer��С-�����nPicModeΪ0��Ϊ֮ǰ�ĸ��ݻ�ȡ���������ֱ��������л������룻���nPicModeΪ1���ϲ�������õķֱ��������뻺�棩
    unsigned int*  pPicSize;     //ʵ��ͼƬ��С
    unsigned int   nPicWidth;    //����ץͼ��-nPicModeΪ1ʱ��Ч���ҿ�>=32,nPicWidth*nPicHeight<5000w�ֱ��ʡ�
    unsigned int   nPicHeight;   //����ץͼ��-nPicModeΪ1ʱ��Ч���Ҹ�>=32,nPicWidth*nPicHeight<5000w�ֱ��ʡ�
    unsigned char  chReserve[8]; //reserve�����ֶ�
}D3D_PIC_INFO;

/*��Ⱦͼ���������*/
typedef enum tagPLAYM4PostProcType
{
    PLAYM4_PPT_BRIGHTNESS               = 0x1,            ///< ����   [-1.0, 1.0]
    PLAYM4_PPT_HUE                      = 0x2,            ///< ɫ��   [0.0, 1.0]----0.166�ۼ�Ϊһ����ɫ�仯��0��1Ϊͬһ����ɫ
    PLAYM4_PPT_SATURATION               = 0x3,            ///< ���Ͷ� [-1.0, 1.0]
    PLAYM4_PPT_CONTRAST                 = 0x4,            ///< �Աȶ� [-1.0, 1.0]
    PLAYM4_PPT_SHARPNESS                = 0x5,            ///< ���   [ 0.0, 1.0]
}PLAYM4PostProcType;

#endif


//////////////////////////////////////////////////////////////////////////////
//API
//////////////////////////////////////////////////////////////////////////////
int  PlayM4_GetPort(int* nPort);
int  PlayM4_FreePort(int nPort);

int  PlayM4_OpenFile(int nPort,char * sFileName);
int  PlayM4_CloseFile(int nPort);
int  PlayM4_SetStreamOpenMode(int nPort,unsigned int nMode);
int  PlayM4_GetStreamOpenMode(int nPort);
int  PlayM4_OpenStream(int nPort,unsigned char * pFileHeadBuf,unsigned int nSize,unsigned int nBufPoolSize);
int  PlayM4_CloseStream(int nPort);

int  PlayM4_Play(int nPort, PLAYM4_HWND hWnd);
int  PlayM4_PlayEx(int nPort, PLAYM4_HWNDEX hWnd);
int  PlayM4_Stop(int nPort);
int  PlayM4_Pause(int nPort,unsigned int nPause);
int  PlayM4_Fast(int nPort);
int  PlayM4_Slow(int nPort);
int  PlayM4_RefreshPlay(int nPort);
int  PlayM4_InputData(int nPort,unsigned char * pBuf,unsigned int nSize);

int  PlayM4_PlaySound(int nPort);
int  PlayM4_StopSound();
int  PlayM4_PlaySoundShare(int nPort);
int  PlayM4_StopSoundShare(int nPort);
int  PlayM4_SetVolume(int nPort,unsigned short nVolume);
unsigned short  PlayM4_GetVolume(int nPort);
//������Ƶ����״̬�͵ȼ�  nEnable: ����ANR���뿪�أ�ȡֵ0��1, Ĭ�Ͽ���  nANRLevel: ANR����ȼ���ȡֵ[0, 5], Ĭ�ϵȼ�Ϊ3
int  PlayM4_SetANRParam(int nPort, int nEnable, int nANRLevel);

int  PlayM4_OneByOne(int nPort);
int  PlayM4_OneByOneBack(int nPort);

int  PlayM4_SetPlayPos(int nPort,float fRelativePos);
float  PlayM4_GetPlayPos(int nPort);

unsigned int  PlayM4_GetFileTime(int nPort);
unsigned int  PlayM4_GetPlayedTime(int nPort);
unsigned int  PlayM4_GetPlayedFrames(int nPort);
unsigned int  PlayM4_GetFileTotalFrames(int nPort);
unsigned int  PlayM4_GetCurrentFrameRate(int nPort);
unsigned int  PlayM4_GetCurrentFrameNum(int nPort);
unsigned int  PlayM4_GetSpecialData(int nPort);
unsigned int  PlayM4_GetAbsFrameNum(int nPort); 
unsigned int  PlayM4_GetFileHeadLength();
unsigned int  PlayM4_GetSdkVersion();
unsigned int  PlayM4_GetLastError(int nPort);
unsigned int  PlayM4_GetPlayedTimeEx(int nPort);

int  PlayM4_GetSystemTime(int nPort, PLAYM4_SYSTEM_TIME *pstSystemTime);
int  PlayM4_GetFileTimeEx(int nPort, unsigned int* pStart, unsigned int* pStop, unsigned int* pRev);
int  PlayM4_GetCurrentFrameRateEx(int nPort, float* pfFrameRate);
int  PlayM4_GetPictureSize(int nPort,int *pWidth,int *pHeight);
int  PlayM4_GetKeyFramePos(int nPort,unsigned int nValue, unsigned int nType, PFRAME_POS pFramePos);
int  PlayM4_GetNextKeyFramePos(int nPort,unsigned int nValue, unsigned int nType, PFRAME_POS pFramePos);

int  PlayM4_ConvertToBmpFile(char * pBuf,int nSize,int nWidth,int nHeight,int nType,char *sFileName);
int  PlayM4_ConvertToJpegFile(char * pBuf,int nSize,int nWidth,int nHeight,int nType,char *sFileName);
int  PlayM4_SetJpegQuality(int nQuality);
int  PlayM4_GetBMP(int nPort,unsigned char * pBitmap,unsigned int nBufSize,unsigned int* pBmpSize);
int  PlayM4_GetJPEG(int nPort,unsigned char * pJpeg,unsigned int nBufSize,unsigned int* pJpegSize);

int  PlayM4_SetPlayedTimeEx(int nPort,unsigned int nTime);
int  PlayM4_SetCurrentFrameNum(int nPort,unsigned int nFrameNum);
int  PlayM4_SetDisplayRegion(int nPort,unsigned int nRegionNum, HKRECT *pSrcRect, PLAYM4_HWND hDestWnd, int bEnable);
int  PlayM4_SetDisplayRegionOnWnd(int nPort,unsigned int nRegionNum, HKRECT *pSrcRect, int bEnable);///<�ര�ڷָ�ӿ�
int  PlayM4_SetDecodeFrameType(int nPort,unsigned int nFrameType);
int  PlayM4_SetSecretKey(int nPort, int lKeyType, char *pSecretKey, int lKeyLen);

int  PlayM4_SetDecCBStream(int nPort,unsigned int nStream);
int  PlayM4_SetDecCallBackMend(int nPort,void (CALLBACK* DecCBFun)(int nPort,char * pBuf,int nSize,FRAME_INFO * pFrameInfo, void* nUser,int nReserved2), void* nUser);
int  PlayM4_SetDecCallBackExMend(int nPort, void (CALLBACK* DecCBFun)(int nPort, char* pBuf, int nSize, FRAME_INFO* pFrameInfo, void* nUser, int nReserved2), char* pDest, int nDestSize, void* nUser);

int  PlayM4_SetDisplayCallBack(int nPort,void (CALLBACK* DisplayCBFun)(int nPort,char * pBuf,int nSize,int nWidth,int nHeight,int nStamp,int nType,int nReserved));
int  PlayM4_SetDisplayCallBackEx(int nPort,void (CALLBACK* DisplayCBFun)(DISPLAY_INFO *pstDisplayInfo), void* nUser);
int  PlayM4_SetFileRefCallBack(int nPort, void (CALLBACK *pFileRefDone)(unsigned int nPort,void* nUser),void* nUser);
int  PlayM4_SetEncTypeChangeCallBack(int nPort, void(CALLBACK *funEncChange)(int nPort, void* nUser), void* nUser);
int  PlayM4_SetCheckWatermarkCallBack(int nPort, void(CALLBACK* funCheckWatermark)(int nPort, WATERMARK_INFO* pWatermarkInfo, void* nUser), void* nUser);
int  PlayM4_SetFileEndCallback(int nPort, void(CALLBACK*FileEndCallback)(int nPort, void *pUser), void *pUser);
int  PlayM4_GetFileTotalTime(int nPort, PLAYM4_SYSTEM_TIME *pstBegin, PLAYM4_SYSTEM_TIME *pstStop);

int  PlayM4_SetYUVCallBackType(int nPort, unsigned int nType, unsigned int nMode);

int  PlayM4_ResetSourceBuffer(int nPort);
int  PlayM4_SetDisplayBuf(int nPort, unsigned int nNum);
int  PlayM4_ResetBuffer(int nPort,unsigned int nBufType);
unsigned int  PlayM4_GetSourceBufferRemain(int nPort);
unsigned int  PlayM4_GetDisplayBuf(int nPort);
unsigned int  PlayM4_GetBufferValue(int nPort,unsigned int nBufType);

int  PlayM4_GetRefValue(int nPort,unsigned char  *pBuffer, unsigned int *pSize);
int  PlayM4_SetRefValue(int nPort,unsigned char  *pBuffer, unsigned int nSize);
int  PlayM4_GetRefValueEx(int nPort,unsigned char *pBuffer, unsigned int *pSize);///< ����֡���ͻص�

int  PlayM4_RegisterDrawFun(int nPort,void (CALLBACK* DrawFun)(int nPort,PLAYM4_HDC hDc,void* nUser),void* nUser);

int  PlayM4_ThrowBFrameNum(int nPort,unsigned int nNum);
int  PlayM4_SkipErrorData(int nPort, int bSkip);

int  PlayM4_ReversePlay(int nPort);

#ifndef LOG_TAG
#define LOG_TAG
typedef enum _PLAYM4_LOG_LEVEL
{
	PLAYM4_LOG_LEVEL_TRACE  = 0,        //
	PLAYM4_LOG_LEVEL_DEBUG  = 1,        //���Լ���
	PLAYM4_LOG_LEVEL_INFO   = 2,        //��Ϣ
	PLAYM4_LOG_LEVEL_WARN   = 3,        //����
	PLAYM4_LOG_LEVEL_ERROR  = 4         //����
}PLAYM4_LOG_LEVEL;
#endif
PLAYM4_API int __stdcall PlayM4_SetPlayCtrlLogFlag(bool bFlag, char* pConfigFilePath, PLAYM4_LOG_LEVEL emLogLevel);

//˽����Ϣ�ص��ӿڣ�nType��ʾ��Ҫ�ص���˽����Ϣ���ͣ�Ŀǰ֧����������: ��ͨĿ���1; ��������Ŀ��� 2; ֧������ 1|2 ����ʽ��������3��ʾ�������Ͷ���ص�
PLAYM4_API int __stdcall PlayM4_RegisterIVSDrawFunCB_EX(int nPort, void (CALLBACK* IVSDrawFun)(int nPort, PLAYM4_HDC hDC, FRAME_INFO* pFrameInfo, INTEL_INFO_EX* pSyncData, void*  dwUser), void*  dwUser, unsigned int nType);

//�������ʾ�ص��о���ʱ�����֡�ţ������ʱ�����֡�ţ��Ļص�����;
// nModule ��ʾ�ص�ģ��ѡ��0 ��ʾĬ�Ͻ���ص�����ʾ�ص� 1����ʾ����ص���2����ʾ��ʾ�ص���
// nType ��ʾ�ص�����ʱ�����֡�ţ��������ʱ�����֡�ţ����������ã�0����ʾ�ص����ʱ��������֡�� 1: ��ʾ�ص�����ʱ����;���֡��
//��ʾ�ص���û��֡�Żص��ģ�������ʾ�ص��� 0����ʾ�ص����ʱ��� 1: ��ʾ�ص�����ʱ���
int  PlayM4_SetDecOrDisplayCallbackType(int nPort, int nModule, int nType);

#define SOFT_DECODE_ENGINE 0 ///<�����
#define HARD_DECODE_ENGINE 1 ///<Ӳ����
//Linux739�汾��ʼ֧��Ӳ��
PLAYM4_API int __stdcall PlayM4_SetDecodeEngine(int nPort, unsigned int nDecodeEngine);
//��ȡ��������
PLAYM4_API unsigned long __stdcall PlayM4_GetDecodeEngine(int nPort);

PLAYM4_API int __stdcall PlayM4_GetEngineSupport(int nPort, ENGINESUPPORT* pstEngineSupport);
PLAYM4_API bool __stdcall PlayM4_SetDisplayCallBackYUV(int nPort, void (CALLBACK* DisplayCBFun)(DISPLAY_INFO_YUV *pstDisplayInfo), bool bTrue, void* pUser);
//���ý������� ����rtmp��ʽ���� 
PLAYM4_API int __stdcall PlayM4_SetIdemuxPara(int nPort, int nChunkSize);
//���ý��������ȫ��ʱ���׼ֵ
PLAYM4_API int __stdcall PlayM4_SetGlobalBaseTime(int nPort, PLAYM4_SYSTEM_TIME stGlobalBaseTime);
// ��ȡ������Я����ʱ��ƫ����Ϣ������еĻ���
PLAYM4_API int __stdcall PlayM4_GetTimeZoneInfo(int nPort, int* pTimeZone);

#ifndef PLAYM4_SESSION_INFO_TAG
#define PLAYM4_SESSION_INFO_TAG
//nProtocolType
#define PLAYM4_PROTOCOL_RTSP    1
//nSessionInfoType
#define PLAYM4_SESSION_INFO_SDP 1

typedef struct _PLAYM4_SESSION_INFO_     //������Ϣ�ṹ
{
    int            nSessionInfoType;   //������Ϣ���ͣ�����SDP�����纣������˽����Ϣͷ
    int            nSessionInfoLen;    //������Ϣ����
    unsigned char* pSessionInfoData;   //������Ϣ����

} PLAYM4_SESSION_INFO;
#endif

PLAYM4_API int __stdcall PlayM4_OpenStreamAdvanced(int nPort, int nProtocolType, PLAYM4_SESSION_INFO* pstSessionInfo, unsigned int nBufPoolSize);

#define R_ANGLE_0   -1  //����ת
#define R_ANGLE_L90  0  //������ת90��
#define R_ANGLE_R90  1  //������ת90��
#define R_ANGLE_180  2  //��ת180��

PLAYM4_API int __stdcall PlayM4_SetRotateAngle(int nPort, unsigned int nRegionNum, unsigned int dwType);

#ifndef PLAYM4_ADDITION_INFO_TAG
#define PLAYM4_ADDITION_INFO_TAG
typedef struct _PLAYM4_ADDITION_INFO_     //������Ϣ�ṹ
{
    unsigned char*  pData;			//��������
    unsigned int    dwDatalen;		//�������ݳ���
    unsigned int	dwDataType;		//��������
    unsigned int	dwTimeStamp;	//���ʱ���
} PLAYM4_ADDITION_INFO;
#endif

//dwGroupIndex ��Լ��ȡֵ0~3����һ�汾ȡ��ͬ��ֻ��ͬ��closestream����
PLAYM4_API int __stdcall PlayM4_SetSycGroup(int nPort, unsigned int dwGroupIndex);
//�ݲ�ʵ�ִ˺�����ͬ�������õ���ʼʱ�䲻һ�£�����С��ʱ����Ϊ������㣬ͬһ���ֻ��һ·
PLAYM4_API int __stdcall PlayM4_SetSycStartTime(int nPort, PLAYM4_SYSTEM_TIME *pstSystemTime);

#ifndef PLAYM4_HIKSR_TAG
#define PLAYM4_HIKSR_TAG

// ��ת��Ԫ�ṹ��
typedef struct tagPLAYM4SRTransformElement
{
    float fAxisX;
    float fAxisY;
    float fAxisZ;
    float fValue; // ��ת�ĽǶ�

}PLAYM4SRTRANSFERELEMENT;


// ��ת��ϲ���
typedef struct tagPLAYM4SRTransformParam
{
    PLAYM4SRTRANSFERELEMENT* pTransformElement;		// ��ת��������
    unsigned int		     nTransformCount;		// ��ת����ϴ���
}PLAYM4SRTRANSFERPARAM;
#endif

// ����ʵ��������صĽӿ�
#ifndef FISH_EYE_TAG
#define FISH_EYE_TAG

// ��������
typedef enum tagFECPlaceType
{
    FEC_PLACE_WALL = 0x1,			// ��װ��ʽ		(����ˮƽ)
    FEC_PLACE_FLOOR = 0x2,			// ���氲װ		(��������)
    FEC_PLACE_CEILING = 0x3,		// ��װ��ʽ		(��������)

}FECPLACETYPE;

typedef enum tagFECCorrectType
{
	FEC_CORRECT_NULL       = 0x0,       // ������(ԭͼ)
	FEC_CORRECT_PTZ        = 0x100,		// PTZ
	FEC_CORRECT_180        = 0x200,		// 180�Ƚ���  ����Ӧ2P��
	FEC_CORRECT_360        = 0x300,		// 360ȫ������ ����Ӧ1P��
    FEC_CORRECT_LAT        = 0x400,     // γ��չ��
	FEC_CORRECT_SEMISPHERE = 0x500,     // 3D�������
    FEC_CORRECT_CYLINDER                = 0x0600, // ����Բ����ʾ - ��װ/��װ
    FEC_CORRECT_CYLINDER_SPLIT          = 0x0700, // �����п���Բ����ʾ - ��װ/��װ
    FEC_CORRECT_PLANET                  = 0x0800, // ����С����
    FEC_CORRECT_ARCSPHERE_HORIZONTAL    = 0x0900, // ����ˮƽ���� - ��װ
    FEC_CORRECT_ARCSPHERE_VERTICAL      = 0x0A00, // ���۴�ֱ���� - ��װ

}FECCORRECTTYPE;

typedef enum tagFECCorrectEffect
{
    FEC_CORRECT_EFFECT_BACK_FACE_CULLING    = 0x100,        // �����޳�����0��ʾ���ã�Ϊ0��ʾ�����ã�������������ǿת������

}FECCORRECTEFFECT;


typedef struct tagCycleParam
{
    float	fRadiusLeft;	// Բ�������X����
    float	fRadiusRight;	// Բ�����ұ�X����
    float   fRadiusTop;		// Բ�����ϱ�Y����
    float   fRadiusBottom;	// Բ�����±�Y����

}CYCLEPARAM;

typedef struct tagPTZParam
{
    float fPTZPositionX;		// PTZ ��ʾ������λ�� X����
    float fPTZPositionY;		// PTZ ��ʾ������λ�� Y����	

}PTZPARAM;

// PTZ��ԭʼ����ͼ����������ʾģʽ
typedef enum tagFECShowMode
{
    FEC_PTZ_OUTLINE_NULL,   // ����ʾ
    FEC_PTZ_OUTLINE_RECT,   // ������ʾ
    FEC_PTZ_OUTLINE_RANGE,  // ��ʵ������ʾ
}FECSHOWMODE; 

// ���±�Ǳ�������

#define 		FEC_UPDATE_RADIUS			 0x1
#define 		FEC_UPDATE_PTZZOOM			 0x2
#define 		FEC_UPDATE_WIDESCANOFFSET	 0x4
#define 		FEC_UPDATE_PTZPARAM			 0x8
#define         FEC_UPDATT_PTZCOLOR          0x10

// ɫ�ʽṹ��
typedef struct tagFECColor
{
    unsigned char nR;     // R����
    unsigned char nG;	  // G����
    unsigned char nB;     // B����
    unsigned char nAlpha; // Alpha����
}FECCOLOR;

typedef struct tagFECParam
{
	unsigned int 	nUpDateType;			// ���µ�����
	unsigned int	nPlaceAndCorrect;		// ��װ��ʽ�ͽ�����ʽ��ֻ�����ڻ�ȡ��SetParam��ʱ����Ч,��ֵ��ʾ��װ��ʽ�ͽ�����ʽ�ĺ�
	PTZPARAM		stPTZParam;				// PTZ У���Ĳ���
	CYCLEPARAM		stCycleParam;			// ����ͼ��Բ�Ĳ���
	float			fZoom;					// PTZ ��ʾ�ķ�Χ����
	float			fWideScanOffset;		// 180����360��У����ƫ�ƽǶ�
    FECCOLOR        stPTZColor;             // PTZ��ɫ
	int				nResver[15];			// �����ֶ�

}FISHEYEPARAM;

#define         FEC_JPEG   0  // JPEGץͼ
#define         FEC_BMP    1  // BMP ץͼ

// Ӳ�����־
#define FEC_DISPLAYSURFACE          0x400  // ����Ӳ���ʶ


//////////*************������صĲ�����ʹ�ýӿںͶ���(����������)************************//////////////

#define FEC_DISPLAYSPHERE           0x402  // ����������Ⱦ��ʾ(����������)-������ʹ��

PLAYM4_API int __stdcall PlayM4_FEC_Rotate(int nPort, PLAYM4SRTRANSFERPARAM *pstRotateParam);///<�˽ӿ�Ϊ������ʹ�ýӿ�(������������ת�ӿ�)

//////////////////////**************************/////////////////////////

///<�µ�3d���۰������������ӽǱ仯����(���ź���ת)
typedef enum tagPLAYM4HRViewParamType
{
    PLAYM4_HR_VPT_ROTATION_X       = 0x1,          ///<ˮƽ��ת
    PLAYM4_HR_VPT_ROTATION_Y       = 0x2,          ///<��ֱ��ת
    PLAYM4_HR_VPT_SCALE            = 0x3,          ///<����(�����ֵΪ������0ֵʱΪ����-����Ч��)
}PLAYM4HRVIEWPARAMTYPE;	

// ����3Dģ�Ͳ���
typedef enum tagPLAYM4FEC3DModelParam
{
    PLAYM4_FEC_3DMP_CYLINDER_HEIGHT              = 0x1,       ///< Բ��ģ�͸�
    PLAYM4_FEC_3DMP_CYLINDER_RADIUS              = 0x2,       ///< Բ��ģ�Ͱ뾶
}PLAYM4FEC3DMODELPARAM;

// �ض��ӽ�״̬
typedef enum tagPLAYM4FECSpecialViewType
{
    PLAYM4_FEC_SVT_EDGE                          = 0x1        ///<��������ģ���봰�������ӽ�
}PLAYM4FECSPECIALVIEWTYPE;


#endif

typedef void (__stdcall * FISHEYE_CallBack )(  void* pUser  , unsigned int  nPort , unsigned int nCBType , void * hDC ,   unsigned int nWidth , unsigned int nHeight); 

// ��������
PLAYM4_API int __stdcall PlayM4_FEC_Enable(int nPort);

// �ر�����ģ��
PLAYM4_API int __stdcall PlayM4_FEC_Disable(int nPort);

// ��ȡ���۽��������Ӷ˿� [1~31] 
PLAYM4_API int  __stdcall PlayM4_FEC_GetPort(int nPort , unsigned int* nSubPort , FECPLACETYPE emPlaceType , FECCORRECTTYPE emCorrectType);

// ɾ�����۽��������Ӷ˿�
PLAYM4_API int __stdcall PlayM4_FEC_DelPort(int nPort , unsigned int nSubPort);

//�������۽���ģʽ
PLAYM4_API int __stdcall PlayM4_FEC_SetConfig(int nPort,unsigned int nType);

// �������۽�������
PLAYM4_API int __stdcall PlayM4_FEC_SetParam(int nPort , unsigned int nSubPort , FISHEYEPARAM * pPara);

// ��ȡ���۽�������
PLAYM4_API int __stdcall PlayM4_FEC_GetParam(int nPort , unsigned int nSubPort , FISHEYEPARAM * pPara);

// ������ʾ���ڣ�������ʱ�л�
PLAYM4_API int __stdcall PlayM4_FEC_SetWnd(int nPort , unsigned int nSubPort , void * hWnd);

// �������۴��ڵĻ�ͼ�ص�
PLAYM4_API int __stdcall PlayM4_FEC_SetCallBack(int nPort , unsigned int nSubPort , FISHEYE_CallBack cbFunc , void * pUser);

PLAYM4_API int __stdcall PlayM4_FEC_Capture(int nPort, unsigned int nSubPort , unsigned int nType, char *pFileName);

PLAYM4_API int __stdcall PlayM4_FEC_GetCurrentPTZPort(int nPort, float fPositionX,float fPositionY, unsigned int *pnPort);

PLAYM4_API int __stdcall PlayM4_FEC_SetCurrentPTZPort(int nPort, unsigned int nSubPort);

PLAYM4_API int __stdcall PlayM4_FEC_SetPTZOutLineShowMode(int nPort,FECSHOWMODE nPTZShowMode);
														 									 
//�µ����۰�������ӽǱ仯(��ת)������ؽӿ�
//��ȡ��������ӽǲ���(����ǰ�Ȼ�ȡ��ǰ��ֵ)
PLAYM4_API int __stdcall PlayM4_FEC_GetViewParam(int nPort, unsigned int nSubPort, PLAYM4HRVIEWPARAMTYPE enViewParamType, float* fValue);
//���ð�������ӽǱ仯����(���õ�ֵΪ��ȡֵ����Ҫƫ��ֵ)
PLAYM4_API int __stdcall PlayM4_FEC_SetViewParam(int nPort, unsigned int nSubPort, PLAYM4HRVIEWPARAMTYPE enViewParamType, float fValue);

//���۵��ӷŴ� nType = 0��
//���۴��ڷָ� nType = 1��
//ע�⣬���ڷָ�ʱhDestWnd��Ч��������ΪNULL��20180813�ݲ�֧�֣�
//Ŀǰ���ӷŴ�֧�����������ϷŴ�nRegionNum��Ϊ0��hDestWnd��ΪNULL��bEnable��Ϊ0ȡ�����ӷŴ󣬷�0Ϊ���ӷŴ�
//pSrcRect�����һ��������1000���Կ���߸ߣ���ֵ��0-1000֮�䣩
//ֻ�Ƽ�ԭͼ��180��360��γ��չ��������PTZ��ʾ�����ӷŴ��ٿ�ptz�ᵼ�µ��ӷŴ�ʧЧ-3D���۲�����ʹ�ô˽ӿ�(���ӽǱ仯�ӿڽ������ţ�
PLAYM4_API bool __stdcall PlayM4_FEC_SetDisplayRegion(int nPort, unsigned int nSubPort,unsigned int nType, unsigned int nRegionNum, HKRECT *pSrcRect, PLAYM4_HWND hDestWnd, int bEnable);
//�����޳�����0��ʾ���ã�Ϊ0��ʾ�����ã�������������ǿת������
PLAYM4_API bool __stdcall PlayM4_FEC_SetCorrectEffect(int nPort, unsigned int nSubPort, FECCORRECTEFFECT nCorrectEffect, float fValue);

// ����3Dģ�Ͳ���-���3DԲ��չ����Ч
PLAYM4_API bool __stdcall PlayM4_FEC_Set3DModelParam(int nPort, unsigned int nSubPort, PLAYM4FEC3DMODELPARAM enType, float fValue);

// ��ȡ�ض��ӽǲ��� - ֻ�����ڻ��棬��SetViewParam�ӿ����ʹ��
PLAYM4_API bool __stdcall PlayM4_FEC_GetSpecialViewParam(int nPort, unsigned int nSubPort, PLAYM4FECSPECIALVIEWTYPE enSVType, PLAYM4HRVIEWPARAMTYPE enVPType, float* pValue);


//ͼ����ǿ���-Linux�汾��֧��
#ifndef PLAYM4_HIKVIE_TAG
#define PLAYM4_HIKVIE_TAG

typedef struct _PLAYM4_VIE_DYNPARAM_
{
    int moduFlag;      //���õ��㷨����ģ�飬��PLAYM4_VIE_MODULES�ж���
    //�� PLAYM4_VIE_MODU_ADJ | PLAYM4_VIE_MODU_EHAN
    //ģ�����ú󣬱���������Ӧ�Ĳ�����
    //PLAYM4_VIE_MODU_ADJ
    int brightVal;     //���ȵ���ֵ��[-255, 255]
    int contrastVal;   //�Աȶȵ���ֵ��[-256, 255]
    int colorVal;      //���Ͷȵ���ֵ��[-256, 255]
    //PLAYM4_VIE_MODU_EHAN
    int toneScale;     //�˲���Χ��[0, 100]
    int toneGain;      //�Աȶȵ��ڣ�ȫ�ֶԱȶ�����ֵ��[-256, 255]
    int toneOffset;    //���ȵ��ڣ�����ƽ��ֵƫ�ƣ�[-255, 255]
    int toneColor;     //��ɫ���ڣ���ɫ����ֵ��[-256, 255]
    //PLAYM4_VIE_MODU_DEHAZE
    int dehazeLevel;   //ȥ��ǿ�ȣ�[0, 255]
    int dehazeTrans;   //͸��ֵ��[0, 255]
    int dehazeBright;  //���Ȳ�����[0, 255]
    //PLAYM4_VIE_MODU_DENOISE
    int denoiseLevel;  //ȥ��ǿ�ȣ�[0, 255]
    //PLAYM4_VIE_MODU_SHARPEN
    int usmAmount;     //��ǿ�ȣ�[0, 255]
    int usmRadius;     //�񻯰뾶��[1, 15]
    int usmThreshold;  //����ֵ��[0, 255]
    //PLAYM4_VIE_MODU_DEBLOCK
    int deblockLevel;  //ȥ��ǿ�ȣ�[0, 100]
    //PLAYM4_VIE_MODU_LENS
    int lensWarp;      //��������[-256, 255]
    int lensZoom;      //��������[-256, 255]
    //PLAYM4_VIE_MODU_CRB
    //����Ӧ����
} PLAYM4_VIE_PARACONFIG;

typedef enum _PLAYM4_VIE_MODULES
{
    PLAYM4_VIE_MODU_ADJ      = 0x00000001, //ͼ���������
    PLAYM4_VIE_MODU_EHAN     = 0x00000002, //�ֲ���ǿģ��
    PLAYM4_VIE_MODU_DEHAZE   = 0x00000004, //ȥ��ģ��
    PLAYM4_VIE_MODU_DENOISE  = 0x00000008, //ȥ��ģ��
    PLAYM4_VIE_MODU_SHARPEN  = 0x00000010, //��ģ��
    PLAYM4_VIE_MODU_DEBLOCK  = 0x00000020, //ȥ���˲�ģ��
    PLAYM4_VIE_MODU_CRB      = 0x00000040, //ɫ��ƽ��ģ��
    PLAYM4_VIE_MODU_LENS     = 0x00000080, //��ͷ�������ģ��
}PLAYM4_VIE_MODULES;
#endif

//���ùر�/����ģ�� -- NO SUPPORT
//dwModuFlag��ӦPLAYM4_VIE_MODULES��,�����
//������ģ�鿪����������ģ��������ڼ����Ĭ�ϵĲ���;
//�ر�ģ����ϴ����õĲ������
//�����ӿڵ��ã������ڸýӿڿ���ģ��󣻷��򣬷��ش���
PLAYM4_API int __stdcall PlayM4_VIE_SetModuConfig(int nPort, int nModuFlag, int bEnable);

//����ͼ����ǿ����NULLȫͼ������ȫͼ������ȫͼ����С����16*16���� -- NO SUPPORT
//��֧�������������Ƚ�˵4������һ���汾����ֻ֧��һ�����������Ҫ�����ص������ص��ͱ���
PLAYM4_API int __stdcall PlayM4_VIE_SetRegion(int nPort, int nRegNum, HKRECT* pRect);

//��ȡ����ģ�� -- NO SUPPORT
PLAYM4_API int __stdcall PlayM4_VIE_GetModuConfig(int nPort, int* pdwModuFlag);

//���ò���
//δ����ģ��Ĳ������ñ����� -- NO SUPPORT
PLAYM4_API int __stdcall PlayM4_VIE_SetParaConfig(int nPort, PLAYM4_VIE_PARACONFIG* pParaConfig);

//��ȡ����ģ��Ĳ��� -- NO SUPPORT
PLAYM4_API int __stdcall PlayM4_VIE_GetParaConfig(int nPort, PLAYM4_VIE_PARACONFIG* pParaConfig);

// ˽����Ϣģ������
typedef enum _PLAYM4_PRIDATA_RENDER
{	
    PLAYM4_RENDER_ANA_INTEL_DATA   = 0x00000001, //���ܷ���
    PLAYM4_RENDER_MD               = 0x00000002, //�ƶ����
    PLAYM4_RENDER_ADD_POS          = 0x00000004, //POS��Ϣ�����
    PLAYM4_RENDER_ADD_PIC          = 0x00000008, //ͼƬ������Ϣ
    PLAYM4_RENDER_FIRE_DETCET      = 0x00000010, //�ȳ�����Ϣ
    PLAYM4_RENDER_TEM              = 0x00000020, //�¶���Ϣ
    PLAYM4_RENDER_TRACK_TEM         = 0x00000040, //�켣��Ϣ
    PLAYM4_RENDER_THERMAL           = 0x00000080, //���������̻�������Ϣ
}PLAYM4_PRIDATA_RENDER;

typedef enum _PLAYM4_THERMAL_FLAG
{
    PLAYM4_THERMAL_FIREMASK           = 0x00000001, //�̻�����
    PLAYM4_THERMAL_RULEGAS            = 0x00000002, //����������
    PLAYM4_THERMAL_TARGETGAS          = 0x00000004, //Ŀ��������
}PLAYM4_THERMAL_FLAG;

typedef enum _PLAYM4_FIRE_ALARM
{
    PLAYM4_FIRE_FRAME_DIS             = 0x00000001, //������ʾ
    PLAYM4_FIRE_MAX_TEMP              = 0x00000002, //����¶�
    PLAYM4_FIRE_MAX_TEMP_POSITION     = 0x00000004, //����¶�λ����ʾ
    PLAYM4_FIRE_DISTANCE              = 0x00000008, //����¶Ⱦ���
}PLAYM4_FIRE_ALARM;

typedef enum _PLAYM4_TEM_FLAG
{
    PLAYM4_TEM_REGION_BOX             = 0x00000001, //�����
    PLAYM4_TEM_REGION_LINE            = 0x00000002, //�߲���
    PLAYM4_TEM_REGION_POINT           = 0x00000004, //�����
}PLAYM4_TEM_FLAG;

typedef enum _PLAYM4_TRACK_FLAG
{
    PLAYM4_TRACK_PEOPLE               = 0x00000001, //�˹켣
    PLAYM4_TRACK_VEHICLE              = 0x00000002, //���켣
}PLAYM4_TRACK_FLAG;

// ������Ϣ����
PLAYM4_API int __stdcall PlayM4_RenderPrivateData(int nPort, int nIntelType, int bTrue);
///<������Ϣ�ӿ���
PLAYM4_API int __stdcall PlayM4_RenderPrivateDataEx(int nPort, int nIntelType, int nSubType, int bTrue);
// ���ö�̬�켣����Ĵ���ʱ��
PLAYM4_API int __stdcall PlayM4_SetTrackDurationTime(int nPort, int nTime);

//ENCRYPT Info
typedef struct{
    long nVideoEncryptType;  //��Ƶ��������
    long nAudioEncryptType;  //��Ƶ��������
    long nSetSecretKey;      //�Ƿ����ã�1��ʾ������Կ��0��ʾû��������Կ
}ENCRYPT_INFO;

// ���������ص�,nType=0��ʾ�������ܱ��λ�����仯�ͻص���nType=1��ʾ�����м���λ�����ص�
PLAYM4_API int __stdcall PlayM4_SetEncryptTypeCallBack(int nPort, unsigned int nType, void (CALLBACK* EncryptTypeCBFun)(int nPort, ENCRYPT_INFO* pEncryptInfo, void* nUser, int nReserved2), void* nUser);

#define PLAYM4_MEDIA_HEAD     1   //ϵͳͷ����
#define PLAYM4_VIDEO_DATA     2   //��Ƶ������
#define PLAYM4_AUDIO_DATA     3   //��Ƶ������
#define PLAYM4_PRIVT_DATA     4   //˽��������

//Ԥ¼��������Ϣ- NO SUPPORT
typedef struct  
{
    long nType;                     // �������ͣ����ļ�ͷ����Ƶ����Ƶ��˽�����ݵ�
    long nStamp;                    // ʱ���
    long nFrameNum;                 // ֡��
    long nBufLen;                   // ���ݳ���
    char* pBuf;                     // ֡���ݣ���֡Ϊ��λ�ص�
    PLAYM4_SYSTEM_TIME  stSysTime;  // ȫ��ʱ��
}RECORD_DATA_INFO;

//����Ԥ¼�񿪹أ�bFlag=1������bFlag=0�ر�-- NO SUPPORT
PLAYM4_API int __stdcall PlayM4_SetPreRecordFlag(int nPort, int bFlag);

//Ԥ¼���������ݻص�- NO SUPPORT
PLAYM4_API int __stdcall PlayM4_SetPreRecordCallBack(int nPort, void (CALLBACK* PreRecordCBfun)(int nPort, RECORD_DATA_INFO* pRecordDataInfo, void* pUser), void* pUser);

typedef struct
{
    long    lDataType;          //˽����������
    long    lDataStrVersion;    //���ݷ��صĽṹ��汾����Ҫ��Ϊ�˼�����
    long    lDataTimeStamp;
    long    lDataLength;
    char*   pData;
}AdditionDataInfo;

PLAYM4_API int __stdcall PlayM4_SetAdditionDataCallBack(int nPort, unsigned int nSyncType, void (CALLBACK* AdditionDataCBFun)(int nPort, AdditionDataInfo* pstAddDataInfo, void* pUser), void* pUser);

//lType: 1 ��ʾ��ȡ��ǰ��ʾ֡PTZ��Ϣ�����ض��ṹ����ʽ�洢��pInfo�ڣ�plLen���س�����Ϣ;���ȴ���pInfo = null�����Ի�ȡ����Ҫ������ڴ泤��plLen
PLAYM4_API int __stdcall PlayM4_GetStreamAdditionalInfo(int nPort, int lType, unsigned char* pInfo, int* plLen);

#define PLAYM4_SOURCE_MODULE             0 // ����Դģ��
#define PLAYM4_DEMUX_MODULE              1 // ����ģ��
#define PLAYM4_DECODE_MODULE             2 // ����ģ��
#define PLAYM4_RENDER_MODULE             3 // ��Ⱦģ��
#define PLAYM4_MANAGER_MODULE            4 // ����ģ��

#define PLAYM4_RTINFO_HARDDECODE_ERROR          0 // Ӳ��������(��Ҫ�����)����
#define PLAYM4_RTINFO_SOFTDECODE_ERROR          1 // �������󣨲�֧�֣�
#define PLAYM4_RTINFO_MEDIAHEADER_ERROR         2 // ý��ͷ����
#define PLAYM4_RTINFO_SWITCH_SOFT_DEC           3 // �л������
#define PLAYM4_RTINFO_ALLOC_MEMORY_ERROR        4 // �ڴ����ʧ��
#define PLAYM4_RTINFO_ENCRYPT_ERROR             5 // ��Կ���� [���ܵ������ڽ�������ʱҲ��ص��Ĵ�����]
#define PLAYM4_RTINFO_RENDER_OVER               8 // ��Ⱦһ֡����
#define PLAYM4_RTINFO_ERR_PRESENT               16 // ��Ⱦ��ʾ����[��ǰ��Ⱦ������Ⱦʧ��,�ϲ������л�����]
#define PLAYM4_RTINFO_IDMX_DATA_ERROR           32 // ��������,����ʧ��
#define PLAYM4_RTINFO_DECODE_PARAM_ERROR        64 // ��������,����ʧ��
#define PLAYM4_RTINFO_SOFTDECODE_DATA_ERROR     128 // ��������ݴ���
#define PLAYM4_RTINFO_IDMX_PSH_PSM_ERROR         0x100// PSH/PSM����,����ʧ��
#define PLAYM4_RTINFO_IDMX_RTP_HEADER_ERROR      0x200// RTPͷ���󣬰�����չͷ
#define PLAYM4_RTINFO_IDMX_RTP_HEADER_SEQ_ERROR  0x400// RTP��Ƶ��������
#define PLAYM4_RTINFO_IDMX_REDUNDANT_ERROR       0x800// ����������������
#define PLAYM4_RTINFO_IDMX_MEDIA_CHANGE_ERROR             0x1000// ý����Ϣ�����ı�(��hikͷ����Ϣ��һ�»���psm���������Ƶ���ͷ����ı�)
#define PLAYM4_RTINFO_IDMX_DIFFERENT_FRAMERATE_ERROR      0x2000// ��װ��֡��������֡�ʲ�һ��
#define PLAYM4_RTINFO_IDMX_DIFFERENT_RESOLUTION_ERROR     0x4000// ��װ��ֱ���������ֱ��ʲ�һ��
#define PLAYM4_RTINFO_IDMX_DECORD_ERROR                   0x8000// �������쳣
#define PLAYM4_RTINFO_IDMX_PRIVT_LEN_ERROR                0x10000// ˽�����ݳ����쳣
#define PLAYM4_RTINFO_SOFTDECODE_DATA_FLAKE_ERROR         0x20000 //��������ݴ��ڻ�������

#define PLAYM4_RTINFO_SOURCE_DATA_INTERVAL      0x40000  // ʵʱ���� ֡ʱ����

typedef struct
{
    int            nRunTimeModule;     //��ǰ����ģ�飬�ݶ�2Ϊ����ģ�飬������չ
    int            nStrVersion;        //���ݷ��صĽṹ��汾����Ҫ��Ϊ�˼�����,��һ���汾�����0x0001
    int            nFrameTimeStamp;    //֡��
    int            nFrameNum;          //ʱ���
    int            nErrorCode;         //������,0ΪӲ�����
    unsigned char  reserved[12];       //�����ֽ�
}RunTimeInfo;

///<ʵʱ��Ϣ�ص��ӿ�
PLAYM4_API int __stdcall PlayM4_SetRunTimeInfoCallBackEx(int nPort, int nModule, void (CALLBACK* RunTimeInfoCBFun)(int nPort, RunTimeInfo* pstRunTimeInfo, void* pUser), void* pUser);

// 1��SetRunTimeInfoCallBackEx�ӿڣ�nErrorCode����6��Ϊ����8���Ժ���չ��ʽ 16��32��64���Ҵ�8��ʼ��ϢĬ�Ϲرղ����͡�
// 2��������Ϣ���ƽӿڣ����ƴ�8�Ժ����Ϣ��֧�ִ�8��ʼ����Ϣ��ƴ��ģʽ 8|16|32 ���ַ�ʽ���ϲ�����ѡ��������͡�
// 3��nType����ͨ����ķ�ʽ�����ʹ��룬nFlag��ʾ�����Ϊ0�����߽��лص�����0����
PLAYM4_API int __stdcall PlayM4_SetRunTimeInfoCallbackType(int nPort, int nModule, unsigned int nType, int nFlag);


///<��Ⱦ��ץͼ:nType:0-jpeg,1-bmp.
PLAYM4_API int __stdcall PlayM4_GetD3DCapture(int nPort, unsigned int nType, D3D_PIC_INFO* pstPicInfo);

///<��Ⱦ����-���ò���
PLAYM4_API int __stdcall PlayM4_SetD3DPostProcess(int nPort, PLAYM4PostProcType nPostType, float fValue);

///<��Ⱦ����-��ȡ����
PLAYM4_API int __stdcall PlayM4_GetD3DPostProcess(int nPort, PLAYM4PostProcType nPostType, float* fValue);

///<�ַ����ӵ������·����������ʱ����Ĭ������⣩-playǰ����
PLAYM4_API int __stdcall PlayM4_SetConfigFontPath(int nPort, char* pFontPath);

// �������ʱ���ȡmp4��װ���߶�λƫ��
PLAYM4_API int __stdcall PlayM4_GetMpOffset(int nPort, int nTime, int* nOffset);

// ��ȡ��Ƶ�ķ�װ�ͱ����ʽ
PLAYM4_API int __stdcall PlayM4_GetStreamInfo(int nPort, int* pSysFormat, int* pCodeType);

///<ʱ���ı�ʾ����Ϊ��λ������Ϊ��������Ϊ��-ͬ���ط�
PLAYM4_API bool __stdcall PlayM4_SetSupplementaryTimeZone(int nPort, int nTimeZone); 
///<���Ѿ�����ʱ���򷵻�����ʱ��������ʧ��-ͬ���ط�
PLAYM4_API bool __stdcall PlayM4_GetSupplementaryTimeZone(int nPort, int* pTimeZone); 

////////////////////////////////////

///<���ڴ�С�ı�֪ͨ�ӿ�
PLAYM4_API int __stdcall PlayM4_WndResolutionChange(int nPort);//new add

//������ʹ��
PLAYM4_API int __stdcall PlayM4_SetRunTimeInfoCallBack(int nPort, void (CALLBACK* RunTimeInfoCBFun)(int nPort, RunTimeInfo* pstRunTimeInfo, void* pUser), void* pUser);
int  PlayM4_RigisterDrawFun(int nPort,void (CALLBACK* DrawFun)(int nPort,PLAYM4_HDC hDc,void* nUser),void* nUser);
int  PlayM4_SetDecCallBack(int nPort,void (CALLBACK* DecCBFun)(int nPort,char* pBuf,int nSize,FRAME_INFO * pFrameInfo, void* nReserved1,int nReserved2));
int  PlayM4_SetDecCallBackEx(int nPort,void (CALLBACK* DecCBFun)(int nPort,char * pBuf,int nSize,FRAME_INFO * pFrameInfo, void* nReserved1,int nReserved2), char* pDest, int nDestSize);
int  PlayM4_SetTimerType(int nPort,unsigned int nTimerType,unsigned int nReserved);
int  PlayM4_GetTimerType(int nPort,unsigned int *pTimerType,unsigned int *pReserved);

int  PlayM4_SetDisplayMode(int nPort, unsigned int dwType);
int  PlayM4_SetVideoWindow(int nPort, unsigned int nRegionNum, PLAYM4_HWND hWnd);
/////////////////////////////////////////////////////////////////////////////

////////////////NO SUPPORT///////////////////////////////////////////////////

int          PlayM4_InitDDraw(PLAYM4_HWND hWnd);
int          PlayM4_RealeseDDraw();
#if (WINVER >= 0x0400)
//Note: These funtion must be builded under win2000 or above with Microsoft Platform sdk.
//You can download the sdk from "http://www.microsoft.com/msdownload/platformsdk/sdkupdate/";
int          PlayM4_InitDDrawDevice();
void         PlayM4_ReleaseDDrawDevice();
int          PlayM4_SetDDrawDevice(int nPort, unsigned int nDeviceNum);
int          PlayM4_SetDDrawDeviceEx(int nPort,unsigned int nRegionNum,unsigned int nDeviceNum);
int          PlayM4_GetDDrawDeviceInfo(unsigned int nDeviceNum, char* lpDriverDescription, unsigned int nDespLen, char* lpDriverName, unsigned int nNameLen, HMONITOR* hhMonitor);
int          PlayM4_GetCapsEx(unsigned int nDDrawDeviceNum);
unsigned int PlayM4_GetDDrawDeviceTotalNums();
#endif
int          PlayM4_GetCaps();
int          PlayM4_OpenStreamEx(int nPort, unsigned char* pFileHeadBuf, unsigned int nSize, unsigned int nBufPoolSize);
int          PlayM4_CloseStreamEx(int nPort);
int          PlayM4_InputVideoData(int nPort, unsigned char* pBuf, unsigned int nSize);
int          PlayM4_InputAudioData(int nPort, unsigned char* pBuf, unsigned int nSize);
int          PlayM4_GetFileSpecialAttr(int nPort, unsigned int* pTimeStamp, unsigned int* pFileNum, unsigned int* pReserved);
//int          PlayM4_SetOverlayMode(int nPort, int bOverlay, COLORREF colorKey);
int          PlayM4_GetOverlayMode(int nPort);
int          PlayM4_SetOverlayFlipMode(int nPort, int bTrue);
//COLORREF     PlayM4_GetColorKey(int nPort);
int          PlayM4_SetPicQuality(int nPort, int bHighQuality);
int          PlayM4_GetPictureQuality(int nPort, int* bHighQuality);
int          PlayM4_ResetSourceBufFlag(int nPort);
int          PlayM4_SetDisplayType(int nPort, int nType);
int          PlayM4_GetDisplayType(int nPort);
int          PlayM4_SyncToAudio(int nPort, int bSyncToAudio);
int          PlayM4_RefreshPlayEx(int nPort, unsigned int nRegionNum);
int          PlayM4_AdjustWaveAudio(int nPort, int nCoefficient);
int          PlayM4_SetPlayMode(int nPort, int bNormal);
int          PlayM4_SetColor(int nPort, unsigned int nRegionNum, int nBrightness, int nContrast, int nSaturation, int nHue);
int          PlayM4_GetColor(int nPort, unsigned int nRegionNum, int* pBrightness, int* pContrast, int* pSaturation, int* pHue);
int          PlayM4_SetImageSharpen(int nPort, unsigned int nLevel);
int          PlayM4_SetDeflash(int nPort, int bDefalsh);
int          PlayM4_CheckDiscontinuousFrameNum(int nPort, int bCheck);
int          PlayM4_SetFileEndMsg(int nPort, PLAYM4_HWND hWnd, unsigned int nMsg);
int          PlayM4_SetVerifyCallBack(int nPort, unsigned int nBeginTime, unsigned int nEndTime, void (__stdcall* funVerify)(int nPort, FRAME_POS* pFilePos, unsigned int bIsVideo, unsigned int nUser), unsigned int nUser);
int          PlayM4_SetEncChangeMsg(int nPort, PLAYM4_HWND hWnd, unsigned int nMsg);
int          PlayM4_SetGetUserDataCallBack(int nPort, void(CALLBACK* funGetUserData)(int nPort, unsigned char* pUserBuf, unsigned int nBufLen, unsigned int nUser), unsigned int nUser);
int          PlayM4_SetSourceBufCallBack(int nPort, unsigned int nThreShold, void (CALLBACK* SourceBufCallBack)(int nPort, unsigned int nBufSize, unsigned int dwUser, void* pResvered), unsigned int dwUser, void* pReserved);
int          PlayM4_GetOriginalFrameCallBack(int nPort, int bIsChange, int bNormalSpeed, int nStartFrameNum, int nStartStamp, int nFileHeader, void(CALLBACK *funGetOrignalFrame)(int nPort, FRAME_TYPE* frameType, int nUser), int nUser);
int          PlayM4_GetThrowBFrameCallBack(int nPort, void(CALLBACK* funThrowBFrame)(int nPort, unsigned int nBFrame, unsigned int nUser), unsigned int nUser);
int          PlayM4_SetAudioCallBack(int nPort, void (__stdcall* funAudio)(int nPort, char* pAudioBuf, int nSize, int nStamp, int nType, int nUser), int nUser);
//motionflow
PLAYM4_API int __stdcall PlayM4_MotionFlow(int nPort, unsigned int dwAdjustType);
	

////////////////////////////////////////////////////////////////////////////////

#ifdef __cplusplus
    }
#endif

#endif //_PLAYM4_H_
